# attention_repo

Lean attention repo for first-principles, CI/CD-aware coding workflows.

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

## Usage Guide

### Shortest mental model
For normal day-to-day use:

1. `start` a repo
2. work inside the repo
3. `wrap` the repo and release attention

Use `init` and `reindex` only to maintain the shared registry/menu layer.

Typed commands can use the canonical project key or an alias. Button callbacks always keep the canonical key.

### `work`
This is the active editing phase between `start` and `wrap`.

What it usually includes:

- inspect the assembled context and current task focus
- edit code, docs, or tests in the target repo
- run the repo's normal verification commands
- update task status if the scope changes during the session
- declare intent first if you are changing behavior and have not already done so

Best use cases:

- any real implementation pass
- debugging, refactoring, documentation, or test work
- iterative sessions where task status may need to be refreshed before wrapping

Typical supporting commands during `work`:

```bash
scripts/attention declare-intent <repo-path> ...
scripts/attention update-task <repo-path> --status-markdown "..."
scripts/attention assemble <repo-path>
```

### `start`
Command:

```bash
scripts/attention start <repo-path> [task...]
```

What it does:

- Without task text:
  - opens the repo's current focus by showing `CURRENT_TASK.md`
- With task text:
  - runs `update-task`
  - runs `assemble`
- In Telegram and TUI:
  - asks for confirmation before entering repo focus

Confirmation behavior:

- Telegram: `Yes` / `No` buttons
- TUI: `Y/n`
- CLI wrapper: direct execution with no extra confirmation prompt

Best use cases:

- resume work on a repo
- record the next focus in one command
- assemble current context before editing

Examples:

```bash
scripts/attention start .
scripts/attention start . "Fix Telegram registration routing and verify menu state"
```

### `wrap`
Command:

```bash
scripts/attention wrap <repo-path>
```

What it does:

- runs `map-freshness-check`
- runs `finalize-change`
- runs `sync-state`
- runs `release-attention`

Best use cases:

- end a work session cleanly
- verify repo memory still matches implementation
- leave a coherent final state for the next session or agent
- clear active repo focus without deleting `CURRENT_TASK.md`

Example:

```bash
scripts/attention wrap .
```

### `release-attention`
Command:

```bash
scripts/attention release-attention <repo-path> [--note "..."]
```

What it does:

- marks the repo-local task file with `Attention State: Released`
- records released status in the central index
- keeps the last task summary available for the next `start`

Use it directly only for repairs. Normal flows should reach it through `wrap`.

### `reinit`
Command:

```bash
scripts/attention reinit <repo-path> [--no-salvage-task] [--no-auto-assemble]
```

What it does:

- archives current task/map and attention artifacts under `.attention/recovery/<timestamp>/`
- rebuilds safe templates when `!MAP.md` or `CURRENT_TASK.md` are missing or corrupt
- salvages readable task text into `## Recovered Context` by default
- removes stale freshness/finalize artifacts
- auto-runs `assemble` only if the declaration still validates after recovery

Use it for repo-memory recovery, not normal startup.

### `init`
Command:

```bash
scripts/attention init [--include-skills] [--include-plugins] [--dry-run]
```

What it does:

- scans configured roots for candidate repos
- registers discovered repos into the central control-plane config
- creates missing repo templates during a real init
- refreshes the central index

Best use cases:

- first-time setup
- `Index New` style discovery
- bringing new repos into the shared menu/control-plane surface

Examples:

```bash
scripts/attention init --dry-run
scripts/attention init
scripts/attention init --include-skills
```

### `reindex`
Command:

```bash
scripts/attention reindex
```

What it does:

- reads central `~/.openclaw/attention-repo/config.json`
- rebuilds central `~/.openclaw/attention-repo/index.json`

Best use cases:

- repair menu or status drift
- refresh the shared runtime view after config changes
- verify the central control plane is consistent

Example:

```bash
scripts/attention reindex
```

## Map freshness requirement
- Before `finalize-change`, verify `!MAP.md` is current for all affected entities.
- If responsibilities/endpoints changed, update entity metadata in `!MAP.md` in the same change set.
- If no map changes are needed, record a short no-change justification in `CURRENT_TASK.md` or finalize notes.

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
- Repo entries may define optional `aliases` and `display_name` in central config.
- Alias resolution order is: exact key, exact alias, then fuzzy matching.

## Control Plane State
The official shared control-plane state lives under `~/.openclaw/attention-repo/`.

Files and roles:

- `~/.openclaw/attention-repo/config.json`
  Persistent control-plane source of truth. Registered projects are added here. Discovery roots and other durable settings also live here.
- `~/.openclaw/attention-repo/index.json`
  Derived runtime projection built from `config.json` plus live repo inspection. This file stores menu/status data such as `exists`, `has_map`, `has_task`, `stale`, and last operation timestamps. It is not the registration authority.
- `<repo>/!MAP.md`, `<repo>/CURRENT_TASK.md`, `<repo>/.attention/*`
  Repo-local memory and workflow artifacts.

Registration contract:

1. Registering a project updates `~/.openclaw/attention-repo/config.json`.
2. Reindexing and normal operations refresh `~/.openclaw/attention-repo/index.json`.
3. If `config.json` and `index.json` disagree, `config.json` wins.

Legacy compatibility:

- `attention-config.json` in the skill repo is a legacy fallback from the pre-centralized model.
- It should not remain an active source of truth once central `config.json` is in use.
- Any migration or fallback behavior must preserve the rule that central `config.json` is authoritative.
- If central `config.json` exists but its `projects` registry is empty, attention-repo imports legacy registered projects into central config once and persists them there.
- After central `config.json` contains the expected projects and central `index.json` has been refreshed, the legacy `attention-config.json` can be removed.
