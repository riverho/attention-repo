# Package Release Control

## Purpose

This repo now has a single public install surface:

- package: `@summon-ai/attention-repo`
- CLI: `attention-repo`
- MCP runtime launch: `attention-repo mcp`

The root package owns:

- installation
- MCP runtime dependency closure
- user-facing tool registry
- copy-paste MCP config output

The nested `mcp-server/` package is internal development scaffolding and is marked `private` to avoid accidental separate publication.

## Tool Registry Source Of Truth

The package registry lives in:

- [src/package/registry.js](/Users/river/.openclaw/workspace/projects/attention-repo/src/package/registry.js)

This file defines:

- official v2 MCP tools
- compatibility aliases
- MCP server command metadata
- generated config snippets for clients

The runtime registry in [mcp-server/src/tools.js](/Users/river/.openclaw/workspace/projects/attention-repo/mcp-server/src/tools.js) consumes that shared metadata instead of maintaining a separate name/description list.

## Zero-Barrier User Install

The intended next-user flow is:

```bash
bun install -g @summon-ai/attention-repo
attention-repo setup --key "ak_attention_repo_xxx"
attention-repo status
attention-repo tools
attention-repo mcp-config
```

The user should not need to:

- install a second package for MCP
- guess the MCP command name
- guess the tool names
- manually reconstruct the config snippet

## Release Gate

Before publishing:

1. Confirm `package.json` and `version.json` agree.
2. Run `node tests/test_package_contract.js`.
3. Run `node tests/test_bun_cli.js`.
4. Run `node tests/test_mcp_integration.js`.
5. Run `npm pack --dry-run` or `bun publish --dry-run`.
6. Publish the root package only.

## Bun Release Control

Yes, release control now sits at the root package boundary:

- `package.json` controls the published files, bin, dependencies, and public access
- the MCP SDK dependency is declared at the root package, so the installed CLI can launch `attention-repo mcp`
- the internal `mcp-server/package.json` is not a separate public release path

That gives one package, one install path, and one registry contract to maintain.
