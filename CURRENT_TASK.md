<!-- Last synced: 2026-03-08T06:45:47.446944+00:00 | Version: 3.2.4 -->
# CURRENT_TASK.md

## Status
✅ **COMPLETED** — Telegram Command Normalization (v3.2.4)

## Completed Work

### Telegram Command Normalization (v3.2.4)

**Problem:** Telegram converts `/attention-layer` to `/attention_layer` in bot command menus, but the skill only recognized the dash version.

**Solution:** Updated command prefix check to handle both variants:
- `/attention-layer` → works
- `/attention_layer` → works (Telegram's underscore conversion)
- `!attention-layer` → works
- `!attention_layer` → works

**Implementation:**
```python
# Normalize: replace underscore with dash for consistency
if text.startswith(("/attention", "!attention", "/attention_layer", "!attention_layer")):
    text = text.replace("attention_layer", "attention")
```

**Files Changed:**
| File | Change |
|------|--------|
| `scripts/service_router.py` | Added underscore variant handling in command prefix check |
| `SKILL.md` | Documented both command variants |

## Flow Summary (v3.2.4)

```
/attention-layer OR /attention_layer → Main Menu
    ↓
Select Action → Project Selector
    ↓
Select Project → Confirm
    ↓
Execute → Record in index
```

## Architectural Intent
- Entities: E-ATTN-CLI-01, E-JIT-ENGINE-01
- Pipeline: .github/workflows/ci.yml
- First Principle: Resilience — handle platform quirks (Telegram's underscore conversion) gracefully
- Requires New Entity: False

## Updated
2026-03-08

## Completed Work

### Main Menu for Attention Layer (v3.2.3)

**New UX Flow:**

```
/attention
    ↓
*Attention Layer* — v3.2.2
Index updated: 2026-03-08
Registered: 1 project(s)

Select operation:

[📋 Projects]  [🔍 Assemble]
[✓ Freshness]  [📝 Status]
[▶️ Declare]   [🏁 Finalize]
    ↓
[Click Assemble]
    ↓
*Assemble* — Select project:

📋 summon-A2A-academy
📋 attention-layer

[📋 summon-A2A-academy]  [📋 attention-layer]
    ↓
[Intent Declaration + Confirm]
    ↓
[Execute]
```

**Implementation:**
- `format_main_menu()` — Shows 6 operations in 3 rows of 2
- Menu actions (`menu-assemble`, `menu-freshness`, etc.) trigger project selector
- Project selector shows stale indicators (🔴)
- Flow: Main Menu → Action → Project → Confirm → Execute

**Files Changed:**
| File | Change |
|------|--------|
| `scripts/service_router.py` | Added `format_main_menu()`, menu action handling, project selector flow |

## Flow Summary (v3.2.3)

```
/attention → Main Menu (6 operations in 3x2 grid)
    ↓
Select Action → Project Selector
    ↓
Select Project → Confirm
    ↓
Execute → Record in index
```

## Architectural Intent
- Entities: E-ATTN-CLI-01, E-JIT-ENGINE-01
- Pipeline: .github/workflows/ci.yml
- First Principle: Hierarchical UX — top-level actions first, then drill down to projects
- Requires New Entity: False

## Updated
2026-03-08

## Completed Work

### Row-based Telegram Menu Layout (v3.2.2)

**Problem:** Buttons were stacked vertically (one per row), wasting space and not matching Telegram's native inline keyboard style.

**Solution:** Updated `format_for_telegram()` to support row grouping with 2 buttons per row.

**Implementation:**
- Added `row` field to menu_items for explicit grouping
- Updated `format_project_actions()` — actions in 2x2 grid
- Updated `format_index_menu()` — projects in rows of 2
- Auto-grouping fallback for items without explicit row

**Before:**
```
[🔍 Assemble]
[✓ Freshness]
[📝 Status]
[▶️ Declare]
```

**After:**
```
[🔍 Assemble] [✓ Freshness]
[📝 Status]   [▶️ Declare]
```

**Files Changed:**
| File | Change |
|------|--------|
| `scripts/service_router.py` | Updated `format_for_telegram()` with row grouping; updated menu builders |

## Flow Summary (v3.2.2)

```
/attention
    ↓
[Index Menu — 2 cols]  ← Projects side-by-side
    ↓
[Actions Menu — 2x2]   ← Actions in grid
    ↓
[Confirm] → [Execute]
```

## Architectural Intent
- Entities: E-ATTN-CLI-01, E-JIT-ENGINE-01
- Pipeline: .github/workflows/ci.yml
- First Principle: UX polish — compact, scannable, native Telegram feel
- Requires New Entity: False

## Updated
2026-03-08

## Completed Work

### Persistent Index with Staleness Tracking (v3.2.1)

**Problem:** No visibility into when projects were last checked or if they're stale. Users couldn't tell if !MAP.md drifted from implementation.

**Solution:** Persistent index file (`.attention/index.json`) with automatic staleness detection.

**Index Schema:**
```json
{
  "version": "3.2.1",
  "created_at": "2026-03-08T06:05:23+00:00",
  "last_updated": "2026-03-08T06:05:23+00:00",
  "projects": {
    "attention-layer": {
      "first_seen": "2026-03-08T06:05:23+00:00",
      "operations": {
        "assemble": {
          "timestamp": "2026-03-08T06:05:23+00:00",
          "result": "ok"
        },
        "freshness": {
          "timestamp": "2026-03-08T06:05:23+00:00",
          "result": "ok"
        }
      }
    }
  }
}
```

**Staleness Detection:**
- Tracks days since last `assemble` / `freshness` check
- Warns if > 7 days stale
- Detects if !MAP.md modified since last assemble
- Shows 🔴 for stale, 🟢/✅/⚪ for status

**Visual Indicators in Menu:**
```
*Attention Layer v3.2.1* — Registered Projects

🔴 summon-A2A-academy 📝 (assembled 12d ago, ⚠️ 2 warnings)
✅ attention-layer 📝 (assembled 0d ago)

⚠️ 1 project(s) need attention
_Run freshness check or assemble to update._

_Select a project to see actions._
```

**Automatic Recording:**
- `assemble` → records timestamp + result
- `freshness` → records timestamp + result
- Index auto-updates on every operation

**Implementation:**
- `_load_index()` / `_save_index()` — persistence
- `update_project_index()` — record operations
- `get_project_staleness()` — calculate staleness
- `build_project_index()` — includes staleness info
- `format_index_menu()` — shows warnings + prioritizes stale projects

## Flow Summary (v3.2.1)

```
/attention
    ↓
[Index Menu with Staleness]  ← Shows 🔴 for stale, version, last update
    ↓
[Select Project] → [Actions Menu]
    ↓
[Confirm] → [Execute] → [Record Timestamp]
    ↓
[Auto-refresh Index]
```

## Files Changed
| File | Change |
|------|--------|
| `scripts/service_router.py` | MAJOR — Added index persistence, staleness detection, visual indicators |

## Architectural Intent
- Entities: E-ATTN-CLI-01, E-JIT-ENGINE-01
- Pipeline: .github/workflows/ci.yml
- First Principle: State awareness — know when things are stale before they cause problems
- Requires New Entity: False

## Updated
2026-03-08
