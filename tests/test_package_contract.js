#!/usr/bin/env node

import { readFileSync } from "fs";
import { join } from "path";
import { fileURLToPath } from "url";

import { execPython } from "../mcp-server/src/python-bridge.js";
import { toolDefinitions } from "../mcp-server/src/tools.js";
import {
  MCP_COMMAND,
  OFFICIAL_MCP_TOOLS,
  LEGACY_MCP_ALIASES,
  renderJsonMcpConfig,
} from "../src/package/registry.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = fileURLToPath(new URL(".", import.meta.url));
const projectRoot = join(__dirname, "..");

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf-8"));
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const rootPackage = readJson(join(projectRoot, "package.json"));
const runtimePackage = readJson(join(projectRoot, "mcp-server", "package.json"));
const versionInfo = readJson(join(projectRoot, "version.json"));

assert(rootPackage.version === versionInfo.version, "package.json and version.json must match");
assert(rootPackage.publishConfig?.access === "public", "root package must publish as public");
assert(rootPackage.dependencies?.["@modelcontextprotocol/sdk"], "root package must own MCP SDK dependency");
assert(rootPackage.files.includes("src/package/registry.js"), "tool registry must ship in package files");
assert(rootPackage.files.includes("attention-config.example.json"), "config template must ship in package files");
assert(rootPackage.engines?.node, "package must declare a Node runtime");
assert(!rootPackage.engines?.bun, "package must not require Bun when runtime is Node");
assert(rootPackage.repository?.url?.includes("summon-ai/attention-repo"), "repository URL must point to the canonical organization");
assert(runtimePackage.private === true, "nested mcp-server package must remain private");

const lockfile = readJson(join(projectRoot, "package-lock.json"));
assert(lockfile.packages?.[""]?.name === rootPackage.name, "package-lock must describe the root package");
assert(!lockfile.packages?.[""]?.engines?.bun, "package-lock must not retain a Bun engine requirement");

const configTemplate = readJson(join(projectRoot, "attention-config.example.json"));
assert(configTemplate.$schema === "attention-repo-config-v3", "config template must use the current schema");
assert(configTemplate.paths?.state_root, "config template must document state_root");
assert(configTemplate.projects?.["my-project"]?.entity_resolution?.map_path, "config template must document map/task resolution");

const gitignore = readFileSync(join(projectRoot, ".gitignore"), "utf-8");
assert(gitignore.includes("\\!MAP.md"), "working !MAP.md must be ignored locally");
assert(gitignore.includes("CURRENT_TASK.md"), "working CURRENT_TASK.md must be ignored locally");
assert(gitignore.includes(".attention/canonical-route.json"), "canonical route manifest must be ignored locally");
const canonicalWorkflow = readFileSync(join(projectRoot, ".github", "workflows", "canonical", "declare.yml"), "utf-8");
assert(canonicalWorkflow.includes("git add -f .attention/canonical-route.json"), "canonical workflow must force-add the ignored manifest");

const expectedNames = [...OFFICIAL_MCP_TOOLS, ...LEGACY_MCP_ALIASES].map((tool) => tool.name).sort();
const actualNames = toolDefinitions.map((tool) => tool.name).sort();

assert(JSON.stringify(actualNames) === JSON.stringify(expectedNames), "tool definitions must match package registry");
assert(renderJsonMcpConfig().includes(`"command": "${MCP_COMMAND}"`), "MCP config must point to packaged CLI");

let strictBridgeRejectedProse = false;
try {
  await execPython(["--help"]);
} catch {
  strictBridgeRejectedProse = true;
}
assert(strictBridgeRejectedProse, "Python bridge must reject non-JSON output unless allowRaw is explicit");

console.log("package contract test passed");
