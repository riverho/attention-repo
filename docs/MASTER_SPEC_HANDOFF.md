# Attention Repo - Master Spec Handoff

**Date:** 2026-03-23  
**Audience:** implementation repo maintainers  
**Status:** active handoff note

## Purpose

This repo should now treat the notes master document as the canonical product and launch reference:

- [/Users/river/.openclaw/workspace/notes/attention-repo/MASTER_DESIGN_AND_IMPLEMENTATION.md](/Users/river/.openclaw/workspace/notes/attention-repo/MASTER_DESIGN_AND_IMPLEMENTATION.md)

This handoff exists so implementation work in `projects/attention-repo` tracks the consolidated launch design instead of older fragmented notes.

## What Changed

The notes repo consolidated the active design into one master document covering:

- Bun release packaging
- local `attention-repo setup --key`
- local `attention-repo status`
- local MCP runtime
- official v2 orchestration-complete MCP tool surface
- Attention Lab magic-link and key handoff into local setup

The older fragmented notes were archived after consolidation.

## Immediate Working Rule

When making implementation decisions in this repo, prefer the master design doc over older assumptions in local README or archived notes.

In particular:

- do not optimize for an open-source launch narrative
- treat Bun as the official release/install surface
- treat local MCP as the launch integration path
- treat Attention Lab as the hosted onboarding and key portal
- treat the v2 MCP surface as the target contract

## Current Implementation Priorities

The active critical path is:

1. Bun package
2. working `attention-repo setup --key`
3. working `attention-repo status`
4. packaged local MCP runtime
5. v2 MCP tools
6. demo repo and side-by-side proof

## Required v2 MCP Tool Surface

Target tools:

1. `attention_resolve_scope`
2. `attention_get_constraints`
3. `attention_declare_scope`
4. `attention_assemble_context`
5. `attention_validate_changes`
6. `attention_finalize_audit`

Temporary compatibility with older tool names is acceptable during migration, but not as the long-term contract.

## Likely Follow-Up In This Repo

- align [README.md](/Users/river/.openclaw/workspace/projects/attention-repo/README.md) with the closed Bun launch direction
- align [mcp-server/README.md](/Users/river/.openclaw/workspace/projects/attention-repo/mcp-server/README.md) with the v2 MCP surface
- implement `setup` and `status`
- package the MCP runtime for `bunx`

## Source Of Truth

Canonical product/design doc:

- [/Users/river/.openclaw/workspace/notes/attention-repo/MASTER_DESIGN_AND_IMPLEMENTATION.md](/Users/river/.openclaw/workspace/notes/attention-repo/MASTER_DESIGN_AND_IMPLEMENTATION.md)

If local docs in this repo conflict with that document, the master design doc wins until implementation catches up.
