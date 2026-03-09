---
name: attention_layer
description: First-principles, CI/CD-entity aware attention layer with mandatory architectural intent declaration
user-invocable: true
---

# Attention Layer (v0.3.0)

**First-principles, CI/CD-entity aware attention layer with mandatory architectural intent declaration.**

> *"Before touching code, declare your intent. After changing code, verify your map."*

---

## Quick Start

```bash
# Install (as OpenClaw skill)
git clone https://github.com/openclaw/attention_layer ~/.openclaw/skills/attention_layer

# Register your project
echo '{
  "project_registry": {
    "my-project": {
      "canonical_path": "/path/to/project",
      "source_strategy": "local_only"
    }
  }
}' > ~/.openclaw/skills/attention_layer/attention-config.json

# Start using
/attention_layer                    # Main menu
/attention_layer assemble my-project
```

---

## What is Attention Layer?

Attention Layer forces a strict **OODA loop** (Observe → Orient → Decide → Act) where code edits are gated by:

1. **Architectural intent declaration** — What are you changing and why?
2. **CI/CD entity mapping** — Which deployment boundaries are affected?
3. **Map freshness verification** — Does !MAP.md match implementation?
4. **Finalize reporting** — What changed and how was it validated?

### When to Use

| Stage | Use Attention Layer? | Why |
|-------|---------------------|-----|
| **L1 Prototype** | Optional | Move fast, no gates |
| **L2 Structured** | Recommended | Entity registry exists |
| **L3 Operational** | **Required** | CI/CD injection, finalize reports |
| **L4 Production** | Enforced | Branch protections, deployment checks |

**Use it when:**
- You're modifying code that deploys to production
- Multiple agents/sub-agents touch the same codebase
- You need audit trails of architectural decisions
- You want to prevent "works on my machine" drift

---

## Core Concepts

### 1. !MAP.md — The Ground Truth

Every project has a `!MAP.md` that defines:
- **Purpose** — What this codebase does
- **Architecture Boundaries** — What it won't do
- **Entity Registry** — Files, CI/CD pipelines, endpoints
- **Operational Snapshot** — Version, last sync, status

### 2. CURRENT_TASK.md — The Work in Progress

Tracks the current change:
- Status (In Progress / Completed)
- Affected entities
- Architectural intent summary
- Sync timestamps

### 3. .attention/index.json — The State Machine

Persistent index tracking:
- All operations with timestamps
- Staleness detection (>7 days = warning)
- Sync history (last 10 entries)
- Project operational state

---

## Command Reference

### Main Menu (Telegram)

Type `/attention_layer` to see:

```
*Attention Layer* — v0.3.0

Index updated: 2026-03-08
Registered: 2 project(s)

[📋 Projects]  [🔍 Assemble]
[✓ Freshness]  [📝 Status]
[▶️ Declare]   [🏁 Finalize]
```

**Telegram:** Use `/attention_layer` (underscore is canonical)

---

### CLI Commands

```bash
# Initialize project templates
attention init <repo-path>

# Declare architectural intent (REQUIRED before edits)
attention declare-intent <repo> \
  --affected-entities E-AUTH-01,E-API-02 \
  --deployment-pipeline .github/workflows/deploy.yml \
  --first-principle-summary "Add OAuth2 token validation to auth middleware" \
  --requires-new-entity false

# Assemble context (read !MAP.md, build context)
attention assemble <repo>

# Update task status
attention update-task <repo> \
  --status-markdown "Implemented JWT validation, tests passing"

# Register new entity in !MAP.md
attention register-new-entity <repo> \
  --id E-WEBHOOK-01 \
  --type Webhook \
  --file-path src/webhooks/stripe.ts \
  --ci-cd .github/workflows/deploy.yml \
  --endpoint "POST /webhooks/stripe" \
  --description "Stripe payment event webhook"

# Verify !MAP.md matches implementation
attention map-freshness-check <repo>

# Finalize change (write report, clear task)
attention finalize-change <repo> \
  --tests-command "npm test" \
  --tests-result pass \
  --notes "Ready for review"

# Sync all state files (!MAP.md, CURRENT_TASK.md, index.json)
attention sync-state <repo> \
  --version 0.3.0 \
  --description "Menu-first UX with Telegram integration"

# Clear task file
attention clear-task <repo>
```

---

## Telegram Integration

### Setup

1. **Get a bot token** from @BotFather
2. **Set environment:**
   ```bash
   export ATTENTION_TELEGRAM_BOT_TOKEN="your_token"
   export ATTENTION_TELEGRAM_USERS="your_user_id"  # Optional allowlist
   ```

3. **Run standalone bot** (optional):
   ```bash
   python3 scripts/telegram-handler.py
   ```

4. **Or use via OpenClaw** (recommended):
   - Type `/attention` in Telegram
   - OpenClaw routes to skill
   - Inline keyboards appear automatically

### Telegram Features

| Feature | Description |
|---------|-------------|
| **Inline Keyboards** | 2-column button layout for compact menus |
| **Callback Handling** | Button clicks route back to service router |
| **Session Persistence** | Multi-turn conversations work across messages |
| **Command Normalization** | `/attention_layer` → `/attention_layer` both work |
| **Staleness Indicators** | 🔴 for stale, 🟢/✅/⚪ for status |

### Telegram Flow

```
User: /attention
  ↓
Bot: Main Menu [6 buttons in 3x2 grid]
  ↓
User: [Click 🔍 Assemble]
  ↓
Bot: Project Selector [📋 project-1] [📋 project-2]
  ↓
User: [Click 📋 project-1]
  ↓
Bot: Confirm? [✓ Confirm assemble] [✗ Cancel]
  ↓
User: [Click ✓ Confirm]
  ↓
Bot: [SYSTEM PROMPT]
      You are a Staff Infrastructure Engineer.
      [Assemble output...]
```

---

## Agent Orchestration Integration

### Why Combine with AO?

**Attention Layer** = Guards architectural intent and tracks state
**Agent Orchestration** = Manages distributed agent swarms

Together they enable **L3+ Operational** multi-agent workflows:

```
River: "Build me a payment system"
  ↓
Brad (Orchestrator)
  ├─ Spawns: ArchitectureAgent
  │   └─ Uses Attention Layer
  │       ├─ declare-intent for payment-api
  │       ├─ register-new-entity E-STRIPE-HOOK
  │       └─ assemble → returns context
  │
  ├─ Spawns: BackendAgent
  │   └─ Uses Attention Layer
  │       ├─ declare-intent references E-STRIPE-HOOK
  │       ├─ update-task "Implementing webhook handler"
  │       └─ finalize-change on completion
  │
  ├─ Spawns: FrontendAgent
  │   └─ [same pattern...]
  │
  └─ Collects all finalization reports
      └─ Reports to River: "Payment system built, 3 agents, 5 entities"
```

### Integration Points

| AO Feature | Attention Layer Role |
|------------|---------------------|
| **Session spawn** | Each agent calls `declare-intent` before work |
| **Progress tracking** | `update-task` feeds AO status dashboard |
| **Completion** | `finalize-change` generates AO-compatible reports |
| **State persistence** | `.attention/index.json` survives session restarts |
| **Conflict detection** | Staleness warnings prevent concurrent edit conflicts |

### Recommended AO + Attention Flow

```yaml
# In your AO ritual
on_session_start:
  - attention declare-intent {{repo}} \
      --affected-entities {{assigned_entities}} \
      --deployment-pipeline {{pipeline}}

on_progress:
  - attention update-task {{repo}} \
      --status-markdown "{{progress_summary}}"

on_complete:
  - attention map-freshness-check {{repo}}
  - attention finalize-change {{repo}} \
      --tests-result {{test_status}} \
      --notes "{{completion_notes}}"

on_heartbeat:
  - attention sync-state {{repo}} \
      --version {{git_tag}} \
      --description "AO heartbeat sync"
```

---

## Configuration

### attention-config.json

```json
{
  "$schema": "attention_layer-config-v1",
  "project_registry": {
    "my-api": {
      "canonical_path": "/Users/me/projects/my-api",
      "git_remote": "https://github.com/me/my-api.git",
      "source_strategy": "local_only",
      "entity_resolution": {
        "!MAP.md": "${canonical_path}/!MAP.md"
      }
    },
    "my-frontend": {
      "canonical_path": "/Users/me/projects/my-frontend",
      "source_strategy": "git_clone_if_missing",
      "git_remote": "https://github.com/me/my-frontend.git"
    }
  },
  "path_resolution": {
    "order": ["canonical_path", "workspace_projects", "git_clone"],
    "forbid_disk_wide_search": true
  },
  "validation": {
    "require_canonical_path_exists": true,
    "stale_threshold_days": 7
  }
}
```

---

## Maturity Levels

### L1 Prototype (No Attention Layer)
```
River: "Build X"
Agent: [edits code]
Agent: Done!
```
**Risks:** No audit trail, concurrent edits conflict, no CI/CD awareness.

### L2 Structured (Entity Registry)
```
River: "Build X"
Agent: attention declare-intent ...
Agent: [edits code]
Agent: attention finalize-change ...
```
**Gains:** Audit trail, entity mapping, intent declaration.

### L3 Operational (Current)
```
River: "Build X"
Brad: Spawns 3 agents via AO
Agent-1: attention declare-intent ...
Agent-2: attention declare-intent ...
Agent-3: attention declare-intent ...
[Parallel work with freshness checks]
Brad: Collects finalize reports
```
**Gains:** Multi-agent coordination, staleness detection, operational visibility.

### L4 Production (Future)
- Branch protections enforced
- Deployment gates require finalize reports
- Automated rollback on map staleness
- Cross-repo dependency tracking

---

## Troubleshooting

### "Cannot resolve: my-project"
Add to `attention-config.json`:
```json
"my-project": {
  "canonical_path": "/absolute/path/to/project",
  "source_strategy": "local_only"
}
```

### "Freshness check failed"
Run:
```bash
attention map-freshness-check <repo> --no-change-justification "Legacy shim unchanged"
```

### Telegram buttons not appearing
- Check `ATTENTION_TELEGRAM_BOT_TOKEN` is set
- Verify bot has inline keyboard permissions
- Try both `/attention_layer` and `/attention_layer`

### Index out of sync
```bash
attention sync-state <repo> --version $(git describe --tags) --description "Manual sync"
```

---

## Ecosystem Status

| Integration | Status | Notes |
|-------------|--------|-------|
| OpenClaw CLI | ✅ Ready | All commands available |
| OpenClaw Telegram | ✅ Ready | Inline keyboards supported |
| Agent Orchestration | 🔄 Integration Guide | See AO + Attention Flow above |
| WhatsApp | 🛣️ Planned | Waiting for user demand |
| VS Code Extension | 🛣️ Planned | L4 milestone |

---

## Contributing

1. Fork `openclaw/attention_layer`
2. Create feature branch
3. Run `attention declare-intent` before changes
4. Implement + test
5. Run `attention finalize-change`
6. Open PR with finalize report attached

---

## License

MIT — Fork and adapt for your organization's needs.

---

*Built for the OpenClaw community. L3 Operational, marching to L4.*
