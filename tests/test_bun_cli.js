#!/usr/bin/env node

import { execFileSync } from "child_process";
import { existsSync, mkdtempSync, readFileSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";

const projectRoot = new URL("..", import.meta.url).pathname;
const cliPath = join(projectRoot, "bin", "attention-repo.js");
const attentionHome = mkdtempSync(join(tmpdir(), "attention-cli-"));
const env = {
  ...process.env,
  ATTENTION_REPO_HOME: attentionHome,
};

function run(args) {
  return execFileSync("node", [cliPath, ...args], {
    cwd: projectRoot,
    env,
    encoding: "utf-8",
  });
}

const setupOutput = run(["setup", "--key", "ak_attention_repo_test_123"]);
if (!setupOutput.includes("Attention Repo setup complete")) {
  throw new Error(`Unexpected setup output: ${setupOutput}`);
}

const vaultPath = join(attentionHome, "vault", "keys.json");
if (!existsSync(vaultPath)) {
  throw new Error("Expected setup to create keys.json");
}

const vault = JSON.parse(readFileSync(vaultPath, "utf-8"));
if (vault.active !== "attention-repo") {
  throw new Error(`Expected active product to be attention-repo, got ${vault.active}`);
}

const statusOutput = run(["status"]);
if (!statusOutput.includes("- key: valid")) {
  throw new Error(`Unexpected status output: ${statusOutput}`);
}

const toolsOutput = run(["tools"]);
if (!toolsOutput.includes("attention_resolve_scope") || !toolsOutput.includes("attention_finalize_audit")) {
  throw new Error(`Unexpected tools output: ${toolsOutput}`);
}

const mcpConfigOutput = run(["mcp-config", "codex"]);
if (!mcpConfigOutput.includes('command = "attention-repo"') || !mcpConfigOutput.includes('args = ["mcp"]')) {
  throw new Error(`Unexpected mcp-config output: ${mcpConfigOutput}`);
}

console.log("bun CLI smoke test passed");
