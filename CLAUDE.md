# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A lean, just-in-time attention layer (Lean v3) used as a Claude Code skill. It enforces an OODA-loop workflow: architectural intent must be declared before any code edits, entity IDs must exist in `!MAP.md`, and a finalize report is required after changes. It is currently at **L3 maturity** (CI/CD injection + finalize reports enforced).

## Commands

The skill CLI entry point is `scripts/attention`, which delegates to `scripts/jit-context.py` (Python 3).

**Verify scripts are executable (CI check):**
```bash
test -x scripts/attention && test -x scripts/jit-context.py
```

**Run a single command:**
```bash
scripts/attention --help
scripts/attention init <repo-path>
scripts/attention declare-intent <repo-path> --affected-entities E-ATTN-CLI-01 --deployment-pipeline .github/workflows/ci.yml --first-principle-summary "..." --requires-new-entity false
scripts/attention assemble <repo-path>
scripts/attention update-task <repo-path> --status-markdown "..."
scripts/attention finalize-change <repo-path> --tests-command "scripts/attention --help" --tests-result pass --notes "..."
scripts/attention clear-task <repo-path>
```

There are no automated tests beyond the CI executability check. Functional validation is done by running commands against a real repo path.

## Architecture

Two source files only — no dependencies beyond Python stdlib and `git`:

- **`scripts/attention`** (bash) — CLI gateway; dispatches all subcommands to `jit-context.py`.
- **`scripts/jit-context.py`** (Python 3) — all logic: declaration validation, entity registry parsing, context assembly, finalize report generation.

**Key files in any target repo (created by `init`):**
- `!MAP.md` — architecture doc + entity registry (JSON block between `<!-- ENTITY_REGISTRY_START -->` / `<!-- ENTITY_REGISTRY_END -->`). This is a **living contract**, not a static file.
- `CURRENT_TASK.md` — ephemeral task status; overwritten on every `update-task`.
- `.attention/architectural_intent.json` — written by `declare-intent`, required by all subsequent commands. `.attention/` is gitignored.

**Enforcement rules baked into `jit-context.py`:**
1. `first_principle_summary` must be ≥ 6 words.
2. Entity IDs in `--affected-entities` must exist in `!MAP.md` (unless `--requires-new-entity true`).
3. `--deployment-pipeline` path must exist on disk.
4. Pipeline must match the `ci_cd` field of selected entities.
5. `register-new-entity` is only allowed when `requires_new_entity=true` was declared.

## Workflow (Lean v3.1)

1. `declare-intent`
2. `assemble` (prints context payload to stdout)
3. Implement edits/tests
4. (optional) `register-new-entity`
5. `update-task`
6. **Map freshness check** — update entity metadata in `!MAP.md` if endpoint/behavior changed, or record a `map-no-change-justification` in finalize notes. See `ROOT_CAUSE_MAP_STALENESS.md`.
7. `finalize-change`

## Entity registry format

```json
{
  "entities": [
    {
      "id": "E-EXAMPLE-01",
      "type": "Endpoint",
      "file_path": "src/example.ts",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "GET /example",
      "description": "..."
    }
  ]
}
```

Entity IDs referenced in `declare-intent` must exactly match `id` values here.

## Adding a new entity

Only valid when `--requires-new-entity true` was passed to `declare-intent`. The referenced `--ci-cd` pipeline must exist on disk.

```bash
scripts/attention register-new-entity <repo> \
  --id E-NEW-01 --type Endpoint --file-path src/new.ts \
  --ci-cd .github/workflows/ci.yml \
  --endpoint "POST /new" --description "..."
```
