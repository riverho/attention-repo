#!/usr/bin/env node

import { spawn } from "child_process";
import { dirname, join, resolve } from "path";
import { fileURLToPath } from "url";
import {
  getToolRegistry,
  renderCodexMcpConfig,
  renderJsonMcpConfig,
} from "../src/package/registry.js";
import {
  ATTENTION_HOME_ENV,
  DEFAULT_PRODUCT_KEY,
  detectRepoPath,
  ensureLocalState,
  getConfigPath,
  getMcpEntrypoint,
  getVaultPath,
  loadConfig,
  loadVersion,
  storeProductKey,
  validateStoredKey,
} from "../src/cli/local-state.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = join(__dirname, "..");
const LEGACY_CLI = join(ROOT, "scripts", "attention");
const VERSION = loadVersion(ROOT);
const LEGACY_COMMANDS = new Set([
  "init",
  "init-config",
  "bootstrap-update",
  "start",
  "wrap",
  "declare-intent",
  "assemble",
  "update-task",
  "register-new-entity",
  "map-freshness-check",
  "finalize-change",
  "clear-task",
  "reinit",
  "release-attention",
  "sync-state",
  "repair",
  "reindex",
]);
const LEGACY_ALIASES = new Map([
  ["declare", "declare-intent"],
]);

function printHelp() {
  console.log(`attention-repo (v${VERSION})

USAGE:
  attention-repo <command> [args]

PRIMARY COMMANDS:
  setup --key "<KEY>"
  status
  mcp
  tools [--json]
  mcp-config [json|codex] [--repo <PATH>]

LEGACY WORKFLOW COMMANDS:
  init | init-config | bootstrap-update | start | wrap
  declare-intent | assemble | update-task | register-new-entity
  map-freshness-check | finalize-change | clear-task
  reinit | release-attention | sync-state | repair | reindex

NOTES:
  - Local operator state is stored in ~/.attention by default.
  - Override local state for tests with ${ATTENTION_HOME_ENV}.
  - Legacy workflow commands are proxied to scripts/attention.`);
}

function parseArgs(argv) {
  const [command, ...rest] = argv;
  return { command, rest };
}

function getFlagValue(args, flag) {
  const index = args.indexOf(flag);
  if (index === -1) {
    return null;
  }
  return args[index + 1] ?? null;
}

function hasFlag(args, flag) {
  return args.includes(flag);
}

async function validateKeyRemotely(key) {
  const url = process.env.ATTENTION_REPO_VALIDATE_URL;
  if (!url) {
    return { validated: false, status: "skipped", source: "attention-lab" };
  }

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify({ key }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Remote key validation failed (${response.status}): ${body}`);
  }

  const payload = await response.json().catch(() => ({}));
  return {
    validated: true,
    status: payload.valid === false ? "invalid" : "valid",
    source: payload.source || "attention-lab",
  };
}

async function cmdSetup(args) {
  const key = getFlagValue(args, "--key");
  if (!key) {
    console.error('Usage: attention-repo setup --key "<KEY>"');
    process.exitCode = 1;
    return;
  }

  ensureLocalState();

  let validation = { validated: false, status: "valid", source: "attention-lab" };
  try {
    validation = await validateKeyRemotely(key);
  } catch (error) {
    console.error(String(error.message || error));
    process.exitCode = 1;
    return;
  }

  const record = storeProductKey(DEFAULT_PRODUCT_KEY, key, {
    valid: validation.status !== "invalid",
    source: validation.source,
  });

  console.log("Attention Repo setup complete");
  console.log(`- key stored: yes`);
  console.log(`- key valid: ${record.valid ? "yes" : "no"}`);
  console.log(`- vault: ${getVaultPath()}`);
  console.log(`- config: ${getConfigPath()}`);
  console.log(`- next command: attention-repo status`);
}

function resolveRepoStatus() {
  const configuredRepo = process.env.ATTENTION_REPO_PATH || loadConfig().repo_path || null;
  const repoPath = configuredRepo || detectRepoPath(process.cwd());
  if (!repoPath) {
    return {
      repoStatus: "not detected",
      topologyStatus: "unknown",
      repoPath: null,
    };
  }

  return {
    repoStatus: "detected",
    topologyStatus: detectRepoPath(resolve(repoPath)) === resolve(repoPath) ? "!MAP.md found" : "!MAP.md missing",
    repoPath,
  };
}

function cmdStatus() {
  ensureLocalState();
  const validation = validateStoredKey(DEFAULT_PRODUCT_KEY);
  const mcpEntrypoint = getMcpEntrypoint(ROOT);
  const repo = resolveRepoStatus();

  console.log("Attention Repo Status");
  console.log(`- package: OK`);
  console.log(`- key: ${validation.status}`);
  console.log(`- key source: ${validation.source || "unknown"}`);
  console.log(`- mcp: ${mcpEntrypoint ? "available" : "missing"}`);
  console.log(`- repo: ${repo.repoStatus}`);
  console.log(`- topology: ${repo.topologyStatus}`);
  if (repo.repoPath) {
    console.log(`- repo path: ${repo.repoPath}`);
  }
}

function cmdMcp() {
  const mcpEntrypoint = getMcpEntrypoint(ROOT);
  if (!mcpEntrypoint) {
    console.error("MCP entrypoint not found in package.");
    process.exitCode = 1;
    return;
  }

  const repoPath = process.env.ATTENTION_REPO_PATH || detectRepoPath(process.cwd()) || process.cwd();
  const child = spawn(process.execPath, [mcpEntrypoint], {
    stdio: "inherit",
    env: {
      ...process.env,
      ATTENTION_REPO_PATH: repoPath,
    },
  });

  child.on("exit", (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal);
      return;
    }
    process.exit(code ?? 0);
  });
}

function cmdTools(args) {
  const registry = getToolRegistry();

  if (hasFlag(args, "--json")) {
    console.log(JSON.stringify({ tools: registry }, null, 2));
    return;
  }

  console.log("Attention Repo MCP Tool Registry");
  console.log("");
  console.log("Official v2 tools:");
  for (const tool of registry.filter((entry) => entry.stability === "official")) {
    console.log(`- ${tool.name}: ${tool.description}`);
  }

  console.log("");
  console.log("Compatibility aliases:");
  for (const tool of registry.filter((entry) => entry.stability === "legacy")) {
    const suffix = tool.aliasFor ? ` -> ${tool.aliasFor}` : "";
    console.log(`- ${tool.name}${suffix}: ${tool.description}`);
  }
}

function cmdMcpConfig(args) {
  const format = args[0] && !args[0].startsWith("--") ? args[0] : "json";
  const repoPath = getFlagValue(args, "--repo") || ".";

  if (format === "json") {
    console.log(renderJsonMcpConfig(repoPath));
    return;
  }

  if (format === "codex") {
    console.log(renderCodexMcpConfig(repoPath));
    return;
  }

  console.error(`Unknown mcp-config format: ${format}`);
  console.error('Supported formats: "json", "codex"');
  process.exitCode = 1;
}

function proxyLegacy(command, args) {
  const resolved = LEGACY_ALIASES.get(command) || command;
  const child = spawn(LEGACY_CLI, [resolved, ...args], {
    stdio: "inherit",
    env: process.env,
  });

  child.on("exit", (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal);
      return;
    }
    process.exit(code ?? 0);
  });
}

async function main() {
  const { command, rest } = parseArgs(process.argv.slice(2));

  if (!command || command === "--help" || command === "-h" || command === "help") {
    printHelp();
    return;
  }

  if (command === "setup") {
    await cmdSetup(rest);
    return;
  }

  if (command === "status") {
    cmdStatus();
    return;
  }

  if (command === "mcp") {
    cmdMcp();
    return;
  }

  if (command === "tools") {
    cmdTools(rest);
    return;
  }

  if (command === "mcp-config") {
    cmdMcpConfig(rest);
    return;
  }

  if (LEGACY_COMMANDS.has(command) || LEGACY_ALIASES.has(command)) {
    proxyLegacy(command, rest);
    return;
  }

  console.error(`Unknown command: ${command}`);
  printHelp();
  process.exitCode = 1;
}

main().catch((error) => {
  console.error(String(error.message || error));
  process.exit(1);
});
