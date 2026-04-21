#!/usr/bin/env node
/**
 * MCP Integration Tests
 *
 * Exercises the packaged stdio launch path with the official MCP SDK client.
 */

import { execFileSync } from "child_process";
import { mkdtempSync, mkdirSync, writeFileSync } from "fs";
import { tmpdir } from "os";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { createRequire } from "module";

import {
  LEGACY_MCP_ALIASES,
  OFFICIAL_MCP_TOOLS,
} from "../src/package/registry.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PROJECT_ROOT = join(__dirname, "..");
const CLI_PATH = join(PROJECT_ROOT, "bin", "attention-repo.js");
const require = createRequire(import.meta.url);
const green = (text) => `\x1b[32m${text}\x1b[0m`;
const red = (text) => `\x1b[31m${text}\x1b[0m`;

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function requireSdkModule(specifier) {
  const resolved = require.resolve(specifier, {
    paths: [PROJECT_ROOT, join(PROJECT_ROOT, "mcp-server")],
  });
  return require(resolved);
}

const { Client } = requireSdkModule("@modelcontextprotocol/sdk/client/index.js");
const { StdioClientTransport } = requireSdkModule("@modelcontextprotocol/sdk/client/stdio.js");

function setupTestRepo() {
  const repoPath = mkdtempSync(join(tmpdir(), "attention-mcp-test-"));
  mkdirSync(join(repoPath, ".github", "workflows"), { recursive: true });
  mkdirSync(join(repoPath, "src"), { recursive: true });
  mkdirSync(join(repoPath, ".attention"), { recursive: true });
  execFileSync("git", ["init"], { cwd: repoPath, stdio: "ignore" });

  writeFileSync(
    join(repoPath, ".github", "workflows", "ci.yml"),
    "name: CI\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n",
  );
  writeFileSync(join(repoPath, "src", "main.py"), "# Main entry point\n");
  writeFileSync(
    join(repoPath, "!MAP.md"),
    `# !MAP.md

## Purpose
Test repository

## Entity Registry
<!-- ENTITY_REGISTRY_START -->
{
  "entities": [
    {
      "id": "E-TEST-01",
      "type": "service",
      "file_path": "src/main.py",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "/api/test",
      "description": "Test entity"
    }
  ]
}
<!-- ENTITY_REGISTRY_END -->
`,
  );

  return repoPath;
}

function parseJsonToolResult(result, toolName) {
  const text = result.content?.find((entry) => entry.type === "text")?.text;
  assert(text, `Expected text content from ${toolName}`);
  return JSON.parse(text);
}

async function main() {
  const testRepo = setupTestRepo();
  const stderrChunks = [];
  const transport = new StdioClientTransport({
    command: "node",
    args: [CLI_PATH, "mcp"],
    cwd: PROJECT_ROOT,
    env: {
      ...process.env,
      ATTENTION_REPO_PATH: testRepo,
    },
    stderr: "pipe",
  });
  const client = new Client(
    { name: "attention-repo-test-client", version: "1.0.0" },
    { capabilities: {} },
  );

  if (transport.stderr) {
    transport.stderr.on("data", (chunk) => {
      stderrChunks.push(chunk.toString());
    });
  }

  try {
    await client.connect(transport);

    const discovered = await client.listTools();
    const discoveredNames = discovered.tools.map((tool) => tool.name).sort();
    const expectedNames = [...OFFICIAL_MCP_TOOLS, ...LEGACY_MCP_ALIASES]
      .map((tool) => tool.name)
      .sort();

    assert(
      JSON.stringify(discoveredNames) === JSON.stringify(expectedNames),
      `Tool discovery mismatch.\nExpected: ${expectedNames.join(", ")}\nActual: ${discoveredNames.join(", ")}`,
    );

    const discoveryStderr = stderrChunks.join("").trim();
    assert(
      discoveryStderr === "",
      `Expected clean stderr during MCP startup and discovery, got:\n${discoveryStderr}`,
    );

    const resources = await client.listResources();
    assert(resources.resources.length === 0, "attention-repo should expose an empty resource list");

    const resourceTemplates = await client.listResourceTemplates();
    assert(
      resourceTemplates.resourceTemplates.length === 0,
      "attention-repo should expose an empty resource template list",
    );

    const resolvedScope = parseJsonToolResult(
      await client.callTool({
        name: "attention_resolve_scope",
        arguments: { files: ["src/main.py"] },
      }),
      "attention_resolve_scope",
    );
    assert(resolvedScope.status === "resolved", "attention_resolve_scope should resolve the test entity");
    assert(
      resolvedScope.scope?.entities?.includes("E-TEST-01"),
      "attention_resolve_scope should include E-TEST-01",
    );

    const declaration = parseJsonToolResult(
      await client.callTool({
        name: "attention_declare_scope",
        arguments: {
          entities: ["E-TEST-01"],
          pipelines: [".github/workflows/ci.yml"],
          summary: "Testing packaged MCP tool discovery with real client transport",
        },
      }),
      "attention_declare_scope",
    );
    assert(
      declaration.accepted_entities?.includes("E-TEST-01"),
      "attention_declare_scope should accept E-TEST-01",
    );

    const constraints = parseJsonToolResult(
      await client.callTool({
        name: "attention_get_constraints",
        arguments: {},
      }),
      "attention_get_constraints",
    );
    assert(
      constraints.in_scope_paths?.includes("src/main.py"),
      "attention_get_constraints should report the declared file",
    );

    const assembled = parseJsonToolResult(
      await client.callTool({
        name: "attention_assemble_context",
        arguments: { entities: ["E-TEST-01"] },
      }),
      "attention_assemble_context",
    );
    assert(
      assembled.files_in_scope?.includes("src/main.py"),
      "attention_assemble_context should include the declared file",
    );

    const validation = parseJsonToolResult(
      await client.callTool({
        name: "attention_validate_changes",
        arguments: { files: ["src/main.py"] },
      }),
      "attention_validate_changes",
    );
    assert(validation.status === "pass", "attention_validate_changes should pass for in-scope files");

    const finalize = parseJsonToolResult(
      await client.callTool({
        name: "attention_finalize_audit",
        arguments: {
          testsCommand: "node tests/test_mcp_integration.js",
          testsResult: "pass",
          notes: "Packaged MCP discovery integration test",
        },
      }),
      "attention_finalize_audit",
    );
    assert(finalize.status === "completed", "attention_finalize_audit should complete successfully");

    console.log(green("MCP integration test passed"));
  } finally {
    await transport.close();
  }
}

main().catch((error) => {
  console.error(red(error.stack || String(error)));
  process.exit(1);
});
