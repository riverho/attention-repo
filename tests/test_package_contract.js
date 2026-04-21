#!/usr/bin/env node

import { readFileSync } from "fs";
import { join } from "path";
import { fileURLToPath } from "url";

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
assert(runtimePackage.private === true, "nested mcp-server package must remain private");

const expectedNames = [...OFFICIAL_MCP_TOOLS, ...LEGACY_MCP_ALIASES].map((tool) => tool.name).sort();
const actualNames = toolDefinitions.map((tool) => tool.name).sort();

assert(JSON.stringify(actualNames) === JSON.stringify(expectedNames), "tool definitions must match package registry");
assert(renderJsonMcpConfig().includes(`"command": "${MCP_COMMAND}"`), "MCP config must point to packaged CLI");

console.log("package contract test passed");
