# Telegram Integration for attention_repo

## Purpose
This document describes the live Telegram and OpenClaw integration for attention_repo.

It covers:

- the real runtime architecture
- the simplified user workflow
- callback and command behavior
- config and scanning rules
- the current testing surface

## Runtime Architecture

The primary production path is:

```
Telegram
  -> OpenClaw command plugin
  -> openclaw_router_bridge.py
  -> service_router.py
  -> scripts/attention
  -> repo-local memory + central attention index
```

Main files:

- `openclaw-plugin/attention-repo-telegram/index.ts`
- `scripts/openclaw_router_bridge.py`
- `scripts/service_router.py`
- `scripts/attention`

Important note:

- `scripts/telegram-handler.py` still exists as a thin standalone wrapper and test harness
- it is no longer the primary production integration path

## User-Facing Workflow

Top-level Telegram menu:

- `Projects`
- `Index New`
- `Wrap Up`

User-facing commands:

- `/attention_repo start <project> [task]`
- `/attention_repo init`
- `/attention_repo reinit <project>`
- `/attention_repo wrap <project>`

Meaning:

- `Projects`: browse registered projects and enter the start flow
- `Index New`: scan configured repo roots, show unregistered repo names, and let the user register by exact project name
- `reinit`: recover broken repo-local memory for one project with confirmation first
- `Wrap Up`: run freshness, finalize, sync, and release-attention for a selected project

Project naming rules:

- buttons use the canonical project key internally
- replies can use the canonical key or a configured alias
- menu labels may use a display name derived from config or repo folder name
- exact key and exact alias matches win before fuzzy matching

## Start Flow

Selecting a project from `Projects` runs the start flow:

1. resolve project from the central registry
2. ask for explicit focus confirmation
3. read latest task summary from repo-local memory
4. show status, prompt prefix, and stale warnings
5. if the repo has never been prepared, backfill empty templates safely
6. prompt for the next task or change request
7. next user reply updates task memory and refreshes the map

Confirmation behavior:

- Telegram buttons: `Yes` / `No`
- TUI: `Y/n`

The focus screen uses a prompt-style header such as:

```text
[focus@summon-A2A-academy]
```

## Index New Flow

Selecting `Index New` runs a scoped discovery pass across configured roots such as:

- `~/.openclaw/workspace/projects`
- `~/.openclaw/workspace/skills`

The response shows unregistered repos by name and summarizes already registered repos separately.

Example follow-up:

- `register summon`
- `register all`
- `cancel`

For each selected unregistered repo, attention-repo:

1. adds it to the central registry
2. creates empty `!MAP.md` and `CURRENT_TASK.md` if missing
3. reindexes the central project state
4. confirms what changed

This keeps the interaction natural:

- user picks a project first
- then states the next task
- internal workflow steps stay hidden

## Wrap Flow

Selecting a project from `Wrap Up` runs:

1. `map-freshness-check`
2. `finalize-change`
3. `sync-state`
4. `release-attention`

Outputs:

- `.attention/map_freshness.json`
- `.attention/ATTENTION_FINALIZE.md`
- updated `!MAP.md`
- updated `CURRENT_TASK.md`
- updated central index

Telegram confirms wrap before execution. On success the router returns a released-attention header and offers `Projects` or `Start Again`.

## Reinit Flow

Running `/attention_repo reinit <project>`:

1. resolves the repo key or alias
2. asks for confirmation
3. archives current task/map and relevant attention artifacts
4. rebuilds safe templates when files are missing or corrupt
5. salvages readable task text into the rebuilt `CURRENT_TASK.md`
6. auto-runs `assemble` only when the declaration still validates

## Callback Model

Router callback payloads:

- `attn:list-projects:`
- `attn:init:`
- `attn:menu-wrap:`
- `attn:start:<project>`
- `attn:confirm-start:<project>`
- `attn:wrap:<project>`
- `attn:confirm-wrap:<project>`
- `attn:cancel-confirmation:<project>`

The OpenClaw bridge rewrites them into plugin-safe command callbacks:

- `/attention_repo attn:list-projects:`
- `/attention_repo attn:start:summon`

This keeps Telegram inline buttons working through the OpenClaw command system.

## Source of Truth

### Central control-plane state
Lives under:

- `~/.openclaw/attention-repo/config.json`
- `~/.openclaw/attention-repo/index.json`

Used for:

- registered projects
- cross-project status
- menu rendering
- startup defaults derived from `~/.openclaw/openclaw.json`

Authority rules:

- `config.json` is the persistent source of truth for registered projects and durable control-plane settings.
- `index.json` is a derived projection for runtime/menu/status rendering.
- Registration writes must land in `config.json` first, then refresh `index.json`.
- If the two files disagree, `config.json` is authoritative and `index.json` must be regenerated.

Legacy fallback:

- `attention-config.json` in the skill repo is legacy compatibility state from the older pre-centralized model.
- It may still exist during migration, but it must not remain the active authority once central `config.json` exists.
- Any code path still reading legacy config should be treated as compatibility-only and eventually removed.
- Migration rule: if central `config.json` exists but has an empty `projects` registry, attention-repo imports legacy registered projects into central config once and persists the result there.
- Retirement rule: after central `config.json` contains the expected registered projects and `reindex` has refreshed central `index.json`, the legacy `attention-config.json` can be removed.

### Repo-local memory
Lives in each project:

- `!MAP.md`
- `CURRENT_TASK.md`
- `.attention/architectural_intent.json`
- `.attention/map_freshness.json`
- `.attention/ATTENTION_FINALIZE.md`

Used for:

- project architecture memory
- active task memory
- wrap/finalize artifacts
- released-attention markers in `CURRENT_TASK.md`

## Discovery and Scanning Rules

Normal menu open must not rescan the workspace.

Default discovery scope:

- `~/.openclaw/workspace/projects/*`

Optional discovery scope, only when explicitly requested:

- `~/.openclaw/workspace/skills/*`
- plugin directories

Rules:

- `/attention_repo` reads central config/index only
- `init` performs discovery
- project templates are created only during explicit init/repair flows
- no disk-wide search on menu open

## Setup Notes

### OpenClaw production path
This path depends on:

- the attention-repo Telegram bridge plugin being loaded by OpenClaw
- `/attention_repo` being owned by the plugin, not native skill auto-registration

### Standalone handler path
If using `scripts/telegram-handler.py` directly, optional environment variables remain:

```bash
export ATTENTION_TELEGRAM_BOT_TOKEN="your-bot-token"
export ATTENTION_TELEGRAM_USERS="user-id-1,user-id-2"
```

This wrapper is useful for local testing or custom bot wiring, but it is not the primary production path anymore.

## Testing

Recommended checks:

```bash
# Router output
python3 scripts/service_router.py telegram '/attention_repo'

# OpenClaw bridge output
python3 scripts/openclaw_router_bridge.py --text '/attention_repo' --user-id test-user --platform telegram

# Project picker
python3 scripts/openclaw_router_bridge.py --text '/attention_repo attn:list-projects:' --user-id test-user --platform telegram

# Test suite
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Extending the Menu

If a new action is added:

1. add the router behavior in `service_router.py`
2. keep the callback payload in the `attn:<action>:<project>` style
3. update both Telegram docs and tests
4. do not add new top-level actions unless they earn their place

Design rule:

- top-level menu stays minimal
- complexity should be pushed into project-specific flows, not the home menu

## One-Doc Rule

This file is the authoritative Telegram integration document.

`docs/TELEGRAM_MENU_DESIGN.md` should stay as a short pointer or summary only, to avoid divergence.

For multi-root discovery and how registered skill repos should appear in Telegram selection, see:

- `docs/MULTI_ROOT_DISCOVERY_DESIGN.md`
