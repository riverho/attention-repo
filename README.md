# attention-layer

Lean attention layer for first-principles, CI/CD-aware coding workflows.

## What this does
- Enforces architectural intent declaration before edits.
- Maps work to existing entities in `!MAP.md`.
- Injects relevant CI/CD and runtime files into task context.
- Produces a deterministic finalize report.

## Init
Run once in a target repo:

```bash
scripts/attention init /path/to/repo
```

This creates:
- `!MAP.md` (architecture + entity registry)
- `CURRENT_TASK.md` (ephemeral task status)

## Core usage
Use this 4-step flow:

1. Declare intent (mandatory)
```bash
scripts/attention declare-intent /path/to/repo \
  --affected-entities E-ATTN-CLI-01 \
  --deployment-pipeline .github/workflows/ci.yml \
  --first-principle-summary "Routes validated input into deterministic command execution." \
  --requires-new-entity false
```

2. Assemble context
```bash
scripts/attention assemble /path/to/repo
```

3. Update current task status
```bash
scripts/attention update-task /path/to/repo \
  --status-markdown "Mapped entity and pipeline. Applying changes now."
```

4. Finalize the change
```bash
scripts/attention finalize-change /path/to/repo \
  --tests-command "scripts/attention --help" \
  --tests-result pass \
  --notes "Ready for review"
```

## Map freshness requirement (v3.1 adjustment)
- Before `finalize-change`, verify `!MAP.md` is current for all affected entities.
- If responsibilities/endpoints changed, update entity metadata in `!MAP.md` in the same change set.
- If no map changes are needed, record a short no-change justification in `CURRENT_TASK.md` or finalize notes.
- Root-cause reference: `ROOT_CAUSE_MAP_STALENESS.md`.

## Optional: register a new entity
Only when you declared `--requires-new-entity true`:

```bash
scripts/attention register-new-entity /path/to/repo \
  --id E-NEW-01 \
  --type Endpoint \
  --file-path src/api/new.ts \
  --ci-cd .github/workflows/ci.yml \
  --endpoint "POST /new" \
  --description "New endpoint for ..."
```

## Notes
- `CURRENT_TASK.md` is ephemeral and should be rewritten frequently.
- `.attention/` is local runtime state and is gitignored.
