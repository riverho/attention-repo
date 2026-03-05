# !MAP.md

## Purpose
Lean attention-layer skill for first-principles, CI/CD-aware context assembly.

## Core Commands
- `scripts/attention declare-intent <repo> ...`
- `scripts/attention assemble <repo>`
- `scripts/attention update-task <repo> --status-markdown "..."`
- `scripts/attention finalize-change <repo> ...`

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
    }
  ]
}
<!-- ENTITY_REGISTRY_END -->
