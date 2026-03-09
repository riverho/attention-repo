# !MAP.md

## Purpose
Lean attention_layer skill for first-principles, CI/CD-aware context assembly.

## Core Commands
- `scripts/attention start <repo> [task...]`
- `scripts/attention init`
- `scripts/attention wrap <repo>`
- Internal workflow commands remain available in `scripts/jit-context.py` for low-level repair and debugging.

## Architecture Boundaries
- No background scanners or cron automation.
- No multi-agent chained funnel.
- No markdown significance scoring.
- No write/edit workflow without architectural declaration.

## Maturity Model
- **L1 (Prototype):** no entity mapping, no CI/CD mapping.
- **L2 (Structured):** entity registry exists, declaration required.
- **L3 (Operational):** CI/CD files injected per entity, finalize report required.
- **L4 (Production):** branch protections + tests + deployment verifications enforced.

## Operational Snapshot
- **Version:** 0.3.0
- **Last Sync:** 2026-03-09T04:19:49.803292+00:00
- **Description:** Wrap-up sync via attention CLI
- **Status:** Operational

## Entity Registry
<!-- ENTITY_REGISTRY_START -->
{
  "entities": [
    {
      "id": "E-ATTN-CLI-01",
      "type": "CLI",
      "file_path": "scripts/attention",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "local command entrypoint",
      "description": "CLI gateway for declare-intent, assemble, and finalize lifecycle"
    },
    {
      "id": "E-JIT-ENGINE-01",
      "type": "Engine",
      "file_path": "scripts/jit-context.py",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "local context assembly runtime",
      "description": "First-principles gate and CI/CD context injector"
    },
    {
      "id": "E-ATTN-PLUGIN-01",
      "type": "Plugin",
      "file_path": "openclaw-plugin/attention-layer-telegram/index.ts",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "/attention_layer",
      "description": "OpenClaw plugin bridge that owns Telegram /attention_layer and routes inline callbacks through service_router."
    }
  ]
}
<!-- ENTITY_REGISTRY_END -->
