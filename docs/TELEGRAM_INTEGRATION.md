# Telegram Integration for attention_layer

## Purpose
This document describes the live Telegram and OpenClaw integration for attention_layer.

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

- `openclaw-plugin/attention-layer-telegram/index.ts`
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

- `/attention_layer start <project> [task]`
- `/attention_layer init`
- `/attention_layer wrap <project>`

Meaning:

- `Projects`: browse registered projects and enter the start flow
- `Index New`: discover candidate projects and backfill missing templates
- `Wrap Up`: run freshness, finalize, and sync for a selected project

## Start Flow

Selecting a project from `Projects` runs the start flow:

1. resolve project from the central registry
2. read latest task summary from repo-local memory
3. show status and stale warnings
4. prompt for the next task or change request
5. next user reply updates task memory and refreshes the map

This keeps the interaction natural:

- user picks a project first
- then states the next task
- internal workflow steps stay hidden

## Wrap Flow

Selecting a project from `Wrap Up` runs:

1. `map-freshness-check`
2. `finalize-change`
3. `sync-state`

Outputs:

- `.attention/map_freshness.json`
- `.attention/ATTENTION_FINALIZE.md`
- updated `!MAP.md`
- updated `CURRENT_TASK.md`
- updated central index

## Callback Model

Router callback payloads:

- `attn:list-projects:`
- `attn:init:`
- `attn:menu-wrap:`
- `attn:start:<project>`
- `attn:wrap:<project>`

The OpenClaw bridge rewrites them into plugin-safe command callbacks:

- `/attention_layer attn:list-projects:`
- `/attention_layer attn:start:summon`

This keeps Telegram inline buttons working through the OpenClaw command system.

## Source of Truth

### Central control-plane state
Lives under:

- `~/.openclaw/attention-layer/config.json`
- `~/.openclaw/attention-layer/index.json`

Used for:

- registered projects
- cross-project status
- menu rendering
- startup defaults derived from `~/.openclaw/openclaw.json`

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

## Discovery and Scanning Rules

Normal menu open must not rescan the workspace.

Default discovery scope:

- `~/.openclaw/workspace/projects/*`

Optional discovery scope, only when explicitly requested:

- `~/.openclaw/workspace/skills/*`
- plugin directories

Rules:

- `/attention_layer` reads central config/index only
- `init` performs discovery
- project templates are created only during explicit init/repair flows
- no disk-wide search on menu open

## Setup Notes

### OpenClaw production path
This path depends on:

- the attention-layer Telegram bridge plugin being loaded by OpenClaw
- `/attention_layer` being owned by the plugin, not native skill auto-registration

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
python3 scripts/service_router.py telegram '/attention_layer'

# OpenClaw bridge output
python3 scripts/openclaw_router_bridge.py --text '/attention_layer' --user-id test-user --platform telegram

# Project picker
python3 scripts/openclaw_router_bridge.py --text '/attention_layer attn:list-projects:' --user-id test-user --platform telegram

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
