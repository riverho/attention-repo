# attention-layer Telegram Integration

## Architecture

```
┌─────────────────┐     ┌────────────────────┐     ┌──────────────────┐
│  Telegram Bot   │────▶│  telegram-handler  │────▶│   menu-service   │
│  (webhook/poll) │◀────│  (thin wrapper)    │◀────│  (business logic)│
└─────────────────┘     └────────────────────┘     └──────────────────┘
                                                              │
                                                              ▼
                                                       ┌──────────────┐
                                                       │  attention   │
                                                       │     CLI      │
                                                       └──────────────┘
```

**Separation of concerns:**

| Layer | File | Responsibility |
|-------|------|----------------|
| **Platform** | `telegram-handler.py` | Telegram-specific: webhooks, auth, message formatting |
| **Service** | `menu-service.py` | Business logic: menu flows, session management, CLI calls |
| **Core** | `attention` CLI | Core skill: intent declaration, entity mapping, etc. |

**Adding a new platform (Discord, Web, etc.):**
1. Create `discord-handler.py` (or `web-handler.py`)
2. Import `menu-service.py` and call `process_callback()`
3. Format `MenuResponse` for your platform
4. Zero changes to `menu-service.py` needed

## Setup

### 1. Environment Variables

```bash
export ATTENTION_TELEGRAM_BOT_TOKEN="your-bot-token"
export ATTENTION_TELEGRAM_USERS="user-id-1,user-id-2"  # Optional allowlist
```

### 2. Install Dependencies

```bash
pip install python-telegram-bot  # Or your preferred library
```

### 3. Run Bot

```bash
python3 scripts/telegram-handler.py
```

Or use the example integration code in `telegram-handler.py` to wire into your existing bot.

## Usage

### Command
```
/attention          → Show main menu
/attention assemble → Start assemble flow
```

### Menu Flow
```
[🎯 attention-layer]
    ↓
[Declare Intent]
    ↓
[Select Project: summon-A2A-academy]
    ↓
[Select Entities: E-API-01, E-WORKER-02]
    ↓
[Confirm & Execute]
```

## Security

| Feature | Status |
|---------|--------|
| User allowlist | ✅ Via `ATTENTION_TELEGRAM_USERS` |
| Read-only by default | ✅ Assemble/Freshness/Status need no approval |
| Session expiry | ✅ 5-minute TTL on multi-step flows |
| No disk-wide search | ✅ All paths from `attention-config.json` |

## Extending

### Add new menu action

1. Add handler in `menu-service.py`:
```python
def handle_my_action(project: str) -> MenuResponse:
    stdout, stderr, rc = run_attention_command("my-command", project)
    return MenuResponse(text=f"Result: {stdout}", ...)
```

2. Wire in `process_callback()`:
```python
if callback_id == "my-action":
    return handle_my_action(params.get("project"))
```

3. Add button in `handle_main_menu()`:
```python
MenuItem("my-action", "🚀 My Action", "my-action")
```

### Add Discord support

```python
# discord-handler.py
from menu_service import process_callback, format_discord_response

@bot.slash_command(name="attention")
async def attention_cmd(ctx, action: str = None):
    response = process_callback(action or "main-menu", str(ctx.user.id), "discord")
    await ctx.send(**format_discord_response(response))
```

## Testing

```bash
# Test menu service directly
python3 scripts/menu-service.py test-menu

# Test Telegram handler simulation
python3 scripts/telegram-handler.py

# Test with real bot (set env vars first)
python3 -c "
from telegram-handler import *
# ... integration code
"
```
