# Multi-Root Discovery Design

## Purpose
Make `attention-repo` support multiple repository roots while keeping the runtime lean:

- no workspace-wide scan on `/attention_repo`
- no ambiguous project selection
- no automatic registration of every skill repo
- no split-brain between central registry and Telegram UI

This design is implementation-ready and intentionally minimal.

## Problem
Today the system already has:

- default discovery root: `~/.openclaw/workspace/projects`
- optional discovery root: `~/.openclaw/workspace/skills`
- Telegram menu that renders only registered entries from the central registry

The gap is policy, not raw capability.

Without a clear design, adding `skills` to discovery creates four risks:

1. Telegram becomes noisy or surprising.
2. `/attention_repo` becomes scan-heavy.
3. Duplicate repo names become ambiguous.
4. Discovery state and menu state diverge.

## First-Principles Rules

1. `/attention_repo` must read central state only.
2. Discovery must happen only during explicit maintenance flows such as `init`, `reindex`, or future scoped management commands.
3. A discovered repo does not become selectable until it is registered.
4. Every selectable item must have a stable registry key.
5. Scope must be visible in Telegram when it affects user choice.

## Decisions

### 1. Multi-root support
Support these roots:

- default: `~/.openclaw/workspace/projects`
- optional: `~/.openclaw/workspace/skills`

`skills` stays opt-in for discovery. It is not scanned during normal menu open.

### 2. Telegram selection policy
Telegram shows registered entries only.

It must never scan `projects` or `skills` directly. The menu is built from:

- `~/.openclaw/attention-repo/config.json`
- `~/.openclaw/attention-repo/index.json`

### 3. Registration policy
`init --include-skills` discovers candidates under `skills` and may register them.

Registration remains the moment when a repo becomes part of the operational surface.

### 4. Naming policy
Registry keys must be unique across all scopes.

If two repos share the same basename across `projects` and `skills`, registration must not silently overwrite. The implementation must either:

- fail with a collision error, or
- require an explicit alias

This design chooses: fail and require explicit alias.

### 5. Menu presentation policy
The top-level Telegram menu stays minimal:

- `Projects`
- `Index New`
- `Wrap Up`

No new top-level `Skills` button.

Inside the project picker, registered entries are grouped by scope and labeled:

- `📋` for `projects`
- `🧰` for `skills`

This preserves the lean menu while still making scope visible.

## Target Config Contract

Central config stays under `~/.openclaw/attention-repo/config.json`.

Target shape:

```json
{
  "$schema": "attention-repo-config-v3",
  "paths": {
    "state_root": "~/.openclaw/attention-repo",
    "default_scan_roots": [
      "~/.openclaw/workspace/projects"
    ],
    "optional_scan_roots": {
      "skills": "~/.openclaw/workspace/skills",
      "plugins": "~/.openclaw/plugins"
    }
  },
  "discovery": {
    "mode": "projects_only",
    "max_depth": 1,
    "include_scopes_by_default": [
      "projects"
    ],
    "include_skills_only_when_requested": true,
    "include_plugins_only_when_requested": true,
    "menu_visible_scopes": [
      "projects",
      "skills"
    ]
  },
  "projects": {
    "summon-academy": {
      "canonical_path": "/Users/river/.openclaw/workspace/projects/summon-academy",
      "source_strategy": "local_only",
      "managed": true,
      "source": "projects",
      "scope": "projects",
      "menu_visible": true
    },
    "attention-repo": {
      "canonical_path": "/Users/river/.openclaw/workspace/skills/attention-repo",
      "source_strategy": "local_only",
      "managed": true,
      "source": "skills",
      "scope": "skills",
      "menu_visible": true
    }
  }
}
```

## Data Model Changes

### Registered project record
Each registered entry must persist:

- `canonical_path`
- `source_strategy`
- `managed`
- `source`
- `scope`
- `menu_visible`

`scope` becomes first-class. Today it exists only on discovered candidates.

### Candidate record
Discovered candidates already carry `scope`. Keep that shape and make it the input to registration.

### Index record
The index should copy `scope` from config for fast menu rendering and future filtering, but config remains the source of truth.

## CLI Behavior

### `init`
Keep current behavior:

- `attention init` scans default roots only
- `attention init --include-skills` also scans `skills`

Required refinement:

- preserve candidate `scope` on registration
- reject duplicate names across scopes
- print collisions clearly in the init report

### `reindex`
Rebuild the central index only from registered config entries.

No disk discovery during `reindex`.

### `start` and `wrap`
No discovery changes.

They continue to resolve only registered project names.

## Telegram Behavior

### Main menu
Unchanged:

- `Projects`
- `Index New`
- `Wrap Up`

### Project picker
Selection screen must render registered entries grouped in this order:

1. stale `projects`
2. stale `skills`
3. non-stale `projects`
4. non-stale `skills`

Labeling:

- `🔴 📋 project-name`
- `🔴 🧰 skill-name`
- `📋 project-name`
- `🧰 skill-name`

Footer stays the same.

### Callback model
Unchanged:

- `attn:start:<project>`
- `attn:wrap:<project>`

No scope is added to callback payloads because the registry key is already unique.

## Collision Handling

If a discovered candidate name already exists in the registry with a different canonical path:

- mark it as `collision`
- do not auto-register
- show both paths in the init output
- require a future explicit aliasing flow or manual config edit

This keeps implementation simple and prevents silent clobbering.

## Non-Goals

This design does not introduce:

- dynamic scanning when `/attention_repo` opens
- a separate `Skills` top-level menu
- automatic registration of every skill repo
- plugin repos as first-class selectable entries by default
- nested hierarchy or folder browsing inside Telegram

## Implementation Plan

### Phase 1: Config and registration
1. Extend config schema to persist `scope` and `menu_visible`.
2. Update `register_project()` to accept and store `scope`.
3. Update `detect_project_candidates()` collision reporting.
4. Keep `init --include-skills` as the only skills discovery path.

### Phase 2: Index and router
1. Persist `scope` into index records during reindex/refresh.
2. Update `build_project_index()` to expose scope to the menu layer.
3. Update `format_index_menu()` to label and group `projects` vs `skills`.

### Phase 3: Docs and migration
1. Update config example and Telegram docs.
2. Add migration logic so older configs without `scope` default to:
   - `projects` for entries under known project roots
   - `skills` for entries under known skills root
   - otherwise `discovered`

## Testing Plan

Add or update tests for:

1. `init` default scan registers only `projects`.
2. `init --include-skills` includes `skills`.
3. duplicate basename across roots is reported and not auto-registered.
4. `build_project_index()` preserves scope.
5. Telegram picker labels `📋` vs `🧰` correctly.
6. `/attention_repo` still opens without any workspace scan.

## Acceptance Criteria

This design is complete when all are true:

1. A repo under `~/.openclaw/workspace/skills` can be registered intentionally.
2. Registered skill repos appear in Telegram selection.
3. `/attention_repo` remains registry-only and scan-free at runtime.
4. Name collisions across roots are blocked, not silently merged.
5. The top-level menu remains three actions only.

## Recommended Defaults

Use this default operating model:

- keep `projects` as the default discovery scope
- include `skills` only on explicit init
- show both scopes in the Telegram picker once registered
- treat collisions as errors until an alias flow exists

This is the lean path because it adds capability without adding background work, hidden scans, or UI sprawl.
