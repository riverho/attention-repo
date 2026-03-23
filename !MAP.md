# !MAP.md

## Purpose
A lean, just-in-time attention repo (Lean v3.1) used as a Claude Code skill and published npm package (`@summon-ai/attention-repo`). Enforces an OODA-loop workflow: architectural intent must be declared before code edits, entity IDs must exist in this registry, and a finalize report is required after changes. Distributed as both a CLI (`attention-repo`) and an MCP server for Claude Code integration.

## Runbook
- Build: *(no compile step — pure Python + ESM JS)*
- Test (Python): `python3 -m unittest discover -s tests -p "test_*.py"`
- Test (Node): `node tests/test_bun_cli.js && node tests/test_mcp_integration.js && node tests/test_package_contract.js`
- Lint: *(none configured)*
- Verify executability: `test -x scripts/attention && test -x scripts/jit-context.py`
- Version: `python3 scripts/version_info.py`

## Architecture Boundaries
- **CLI layer (Bash + Python):** `scripts/attention` dispatches to `scripts/jit-context.py` for all workflow logic. No external dependencies — Python stdlib + git only.
- **Node/MCP layer (ESM JS):** `bin/attention-repo.js` + `mcp-server/` provide the packaged CLI and MCP server. Depend on `@modelcontextprotocol/sdk` only.
- **State:** Global attention state stored in `~/.openclaw/attention-repo/`. Per-repo state in `.attention/` (gitignored). Live task in `CURRENT_TASK.md`.
- **Registry contract:** This file (`!MAP.md`) is the authoritative entity registry. All `declare-intent` calls validate against it.

## Non-Goals
- Not a general-purpose task manager — scope is limited to architectural intent and context assembly.
- Does not implement its own LLM calls — bridges to Claude via MCP.
- Does not manage secrets or credentials.

## Operational Snapshot
- **Version:** 0.4.0
- **Last Sync:** 2026-03-23T08:18:01.389056+00:00
- **Description:** Wrap-up sync via attention CLI
- **Status:** Operational

## Entity Registry
<!-- ENTITY_REGISTRY_START -->
{
  "entities": [
    {
      "id": "E-ATTN-CLI-01",
      "type": "Script",
      "file_path": "scripts/attention",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "CLI: attention <command> [args]",
      "description": "Bash CLI gateway. Routes all subcommands (init, start, declare-intent, assemble, finalize-change, wrap, etc.) to jit-context.py. Runs update-gate check before most commands."
    },
    {
      "id": "E-ATTN-ENGINE-01",
      "type": "Script",
      "file_path": "scripts/jit-context.py",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "Python module: all attention subcommands",
      "description": "Core attention engine. Implements init, declare-intent, assemble, update-task, register-new-entity, map-freshness-check, finalize-change, clear-task, reinit, release-attention, sync-state, repair, reindex."
    },
    {
      "id": "E-ATTN-RESOLVE-01",
      "type": "Script",
      "file_path": "scripts/resolve.py",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "Python module: project discovery and central config",
      "description": "Central config, project discovery, and index management. Handles multi-workspace support, ~/.openclaw/attention-repo/config.json persistence, and project key normalization."
    },
    {
      "id": "E-ATTN-STATE-01",
      "type": "Script",
      "file_path": "scripts/attention-state.py",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "Python module: global attention state",
      "description": "Global attention-state wrapper. Provides get_active(), set_active(), release_active(), list_attended(). Called by attention start and release-attention."
    },
    {
      "id": "E-ATTN-VERSION-01",
      "type": "Script",
      "file_path": "scripts/version_info.py",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "Python module: get_version()",
      "description": "Canonical version loader. Reads version.json and exposes get_version(). Used by update-gate check and bootstrap-update."
    },
    {
      "id": "E-ATTN-BIN-01",
      "type": "Module",
      "file_path": "bin/attention-repo.js",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "CLI: attention-repo <command>",
      "description": "Packaged Node.js ESM CLI entry point. Commands: setup --key, status, mcp, tools, mcp-config. Proxies legacy commands to scripts/attention. Published as npm bin."
    },
    {
      "id": "E-ATTN-SRC-LOCAL-01",
      "type": "Module",
      "file_path": "src/cli/local-state.js",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "Node module: vault and repo detection",
      "description": "Local operator state management. Handles vault (keys.json at ~/.attention/vault/), config persistence, key format validation (ak_attention_repo_*), !MAP.md-based repo detection."
    },
    {
      "id": "E-ATTN-SRC-REG-01",
      "type": "Module",
      "file_path": "src/package/registry.js",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "Node module: OFFICIAL_MCP_TOOLS, LEGACY_MCP_ALIASES",
      "description": "Tool registry and MCP configuration renderer. Defines 6 official MCP tools and 5 legacy aliases. Renders JSON and Codex-format MCP configs."
    },
    {
      "id": "E-ATTN-MCP-INDEX-01",
      "type": "MCPServer",
      "file_path": "mcp-server/index.js",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "Stdio MCP server entry point",
      "description": "Stdio-based MCP server. Implements MCP protocol handlers for all attention tools. Entry point for Claude Code integration via .mcp.json."
    },
    {
      "id": "E-ATTN-MCP-TOOLS-01",
      "type": "MCPServer",
      "file_path": "mcp-server/src/tools.js",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "MCP tools: attention_resolve_scope, attention_declare_scope, attention_assemble_context, attention_query, attention_validate_changes, attention_finalize_audit",
      "description": "MCP tool implementations. Loads entity registry from !MAP.md, resolves file-to-entity mappings, builds scoped context, validates git changes against declared intent."
    },
    {
      "id": "E-ATTN-MCP-BRIDGE-01",
      "type": "Module",
      "file_path": "mcp-server/src/python-bridge.js",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "Node module: Python subprocess bridge",
      "description": "Python interpreter detection and jit-context.py subprocess spawning. Parses JSON output from Python CLI. Used by MCP tools to delegate to core engine."
    },
    {
      "id": "E-ATTN-TEST-GATE-01",
      "type": "TestSuite",
      "file_path": "tests/test_gate_effectiveness.py",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "Python unittest: entity registration and declaration gates",
      "description": "11 gate effectiveness tests covering cold start, entity parsing, valid/invalid declarations, and enforcement rules in jit-context.py."
    },
    {
      "id": "E-ATTN-TEST-DRIFT-01",
      "type": "TestSuite",
      "file_path": "tests/test_drift_detection.py",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "Python unittest: freshness check and file drift",
      "description": "6 drift detection tests covering clean state, deleted files, content hash changes, and git conflict scenarios for map-freshness-check."
    },
    {
      "id": "E-ATTN-TEST-AUDIT-01",
      "type": "TestSuite",
      "file_path": "tests/test_audit_chain.py",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "Python unittest: finalize lifecycle enforcement",
      "description": "2 audit chain tests covering finalize blocking and complete workflow execution."
    },
    {
      "id": "E-ATTN-TEST-CLI-01",
      "type": "TestSuite",
      "file_path": "tests/test_bun_cli.js",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "Node test: bin/attention-repo.js smoke tests",
      "description": "Smoke tests for the packaged CLI: setup --key, status, tools registry listing, mcp-config codex rendering."
    },
    {
      "id": "E-ATTN-TEST-MCP-01",
      "type": "TestSuite",
      "file_path": "tests/test_mcp_integration.js",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "Node test: MCP server integration",
      "description": "MCP server integration tests: stdio transport initialization, tool registry matching, MCP SDK client communication."
    },
    {
      "id": "E-ATTN-TEST-PKG-01",
      "type": "TestSuite",
      "file_path": "tests/test_package_contract.js",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "Node test: package contract validation",
      "description": "Package contract tests: version consistency (package.json vs version.json), publish config, tool registry contract, MCP config points to packaged CLI."
    }
  ]
}
<!-- ENTITY_REGISTRY_END -->
