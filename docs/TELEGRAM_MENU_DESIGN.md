# Telegram Menu Flow for attention-layer

## Menu Structure

```
Main Menu
├── [🎯 attention-layer]
│   ├── [Assemble] → Project selection → Execute → Result
│   ├── [Freshness Check] → Project selection → Execute → Result
│   ├── [Status] → Project selection → Show CURRENT_TASK.md
│   └── [Declare Intent] → Project selection → Entity selection → Summary → Confirm
│
├── [Other skills...]
└──
```

## Callback Data Schema

```json
{
  "menu": "attention-layer",
  "action": "assemble|freshness|status|declare-intent",
  "step": "project-select|entity-select|confirm|execute",
  "data": {
    "project": "summon-A2A-academy",
    "entities": ["E-FOO-01"],
    "pipeline": ".github/workflows/ci.yml"
  }
}
```

## Flow: Declare Intent

**Step 1: User taps [🎯 attention-layer]**
```
Bot shows:
━━━━━━━━━━━━━━━━━━━━
🎯 attention-layer
━━━━━━━━━━━━━━━━━━━━
[Assemble] [Freshness]
[Status]   [Declare Intent ⬇️]
```

**Step 2: User taps [Declare Intent]**
```
Bot shows:
━━━━━━━━━━━━━━━━━━━━
🎯 Declare Intent
Select project:
━━━━━━━━━━━━━━━━━━━━
[summon-A2A-academy]
[attention-layer]
[Cancel]
```
Callback: `menu=attention-layer,action=declare-intent,step=project-select`

**Step 3: User selects project**
Bot reads `!MAP.md` from that project, extracts entity IDs.
```
Bot shows:
━━━━━━━━━━━━━━━━━━━━
🎯 Declare Intent: summon-A2A-academy
Select affected entities:
━━━━━━━━━━━━━━━━━━━━
[E-API-01 ☑️] [E-WORKER-02 ☐]
[E-UI-03 ☐]   [New Entity ⬇️]
[Back] [Cancel] [Next ➡️]
```
Callback: `menu=attention-layer,action=declare-intent,step=entity-select,project=summon-A2A-academy`

**Step 4: Entity selection complete → Summary**
```
Bot shows:
━━━━━━━━━━━━━━━━━━━━
🎯 Confirm Intent Declaration

Project: summon-A2A-academy
Entities: E-API-01, E-WORKER-02
Pipeline: .github/workflows/api.yml

First Principle:
[text input or select from presets]
━━━━━━━━━━━━━━━━━━━━
[Back] [Cancel] [✅ Declare]
```

**Step 5: Execute**
Bot runs: `./scripts/attention declare-intent <project> --affected-entities ...`
Returns result or error.

## Implementation Notes

### State Management
- Store temporary state in `memory/telegram-menu-{user_id}.json`
- Expire after 5 minutes of inactivity
- Or use callback data to carry full state (no server storage)

### Security
- Read-only mode: No authentication needed for assemble/status/freshness
- Declare intent: Still considered "safe" (only writes to .attention/, not source code)
- Gate finalize-change and register-new-entity behind approval

### Integration Points
```python
# Telegram bot handler
if callback_data["menu"] == "attention-layer":
    skill_path = "~/.openclaw/workspace/skills/attention-layer"
    config = load_config(f"{skill_path}/attention-config.json")
    
    if callback_data["action"] == "declare-intent":
        if callback_data["step"] == "project-select":
            projects = list_registered_projects(config)
            show_inline_keyboard(projects)
        elif callback_data["step"] == "entity-select":
            project = callback_data["data"]["project"]
            entities = get_entities_from_map(project)
            show_inline_keyboard(entities)
        elif callback_data["step"] == "execute":
            result = run_attention_command(skill_path, callback_data)
            send_message(result)
```

## Files Needed

1. `telegram-menu-handler.py` — Routes callbacks, manages state
2. `attention-layer-formatter.py` — Converts CLI output → Telegram text
3. `config.py` — Reads `attention-config.json`

## MVP Scope

Phase 1 (Option 1 - Read-only):
- [Assemble] → project list → execute → result
- [Freshness Check] → project list → execute → result
- [Status] → project list → show CURRENT_TASK.md

Phase 2 (Safe writes):
- [Declare Intent] → full flow with entity selection

Phase 3 (Gated writes):
- [Finalize Change] → Brad asks for approval
- [Register New Entity] → Brad asks for approval
