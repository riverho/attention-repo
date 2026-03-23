# Attention Repo - OSS Local Boundary

**Status:** active boundary note  
**Date:** 2026-03-23

This document defines the clean cut for the open-source local-testing version of Attention Repo.

## Goal

Make the current repo behave like the OSS local product surface so development can continue against the public-safe version.

The target OSS-local product includes:

- Bun package
- local CLI
- local MCP runtime
- manual `!MAP.md` workflow
- human-higher-involvement workflow
- local tests for CLI and MCP

It does not include the older skill/OpenClaw/Telegram integration layer.

## Kept In OSS Local Surface

- `bin/`
- `src/cli/`
- `mcp-server/`
- core workflow scripts in `scripts/`
- `README.md`
- `tests/test_bun_cli.js`
- `tests/test_mcp_integration.js`
- general Python tests for local workflow behavior

## Archived From OSS Local Surface

- OpenClaw plugin bridge
- Telegram handler and router
- Telegram-specific docs
- skill-only legacy notes

Archive location:

- `_archive/skill-local/`

## Working Rule

When testing or packaging the open-source local version, treat the archived skill/Telegram layer as out of scope.

The OSS-local launch story is:

1. install package
2. run local `setup`
3. run local `status`
4. run local MCP
5. use manual/local repo intelligence workflow
