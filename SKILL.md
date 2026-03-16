---
name: attention-repo
description: First-principles, CI/CD-entity aware attention repo with mandatory architectural intent declaration
user-invocable: true
---

# Attention Repo

**First-principles, CI/CD-entity aware attention repo with mandatory architectural intent declaration.**

> *"Before touching code, declare your intent. After changing code, verify your map."*

---

## Quick Start

```bash
# Install (as OpenClaw skill)
git clone https://github.com/openclaw/attention_repo ~/.openclaw/skills/attention_repo

# Create official central control-plane config
cd ~/.openclaw/workspace/skills/attention-repo
scripts/attention init-config

# Register/discover projects into the official central config
scripts/attention init --dry-run
scripts/attention reindex

# First run after a deployed update
scripts/attention bootstrap-update

# Start using
/attention_repo                    # Main menu
/attention_repo assemble my-project
```

### Start Narrow

<!-- CODEX_START_NARROW_START -->

This section is authoritative for Codex when the user invokes `attention-repo start`.

When the user invokes `attention-repo start`, the default orientation path is intentionally minimal:

1. Read `!MAP.md`
2. Read `CURRENT_TASK.md`
3. Read `.attention/index.json`
4. Stop and summarize:
   - closed branches
   - open branches
   - current narrowing frame
   - whether there is an active or released workstream

Do not continue into source files, broad searches, or extra docs on `start` alone.

Expand beyond those three files only if one of these is true:
- the three artifacts contradict each other
- one of them is missing or clearly stale
- the user's next request specifically requires contract details or implementation proof

If deeper orientation is justified, expand in this order:
1. `docs/PROJECT_MEMORY.md`
2. `docs/_archive/ARCHITECTURE_AUDIT.md`
3. `docs/0.2/training_api_contracts.md`
4. `docs/0.2/training_flow_plan.md`

This is the guardrail:
- minimal orientation first
- no `src/` or `frontend/` reads during `start` unless contradiction forces targeted verification
- no architectural-intent rewrite during `start` unless the user explicitly declares a new work item

<!-- CODEX_START_NARROW_END -->

---

## What is Attention Repo?

Attention Repo forces a strict **OODA loop** (Observe → Orient → Decide → Act) where code edits are gated by:

1. **Architectural intent declaration** — What are you changing and why?
2. **CI/CD entity mapping** — Which deployment boundaries are affected?
3. **Map freshness verification** — Does !MAP.md match implementation?
4. **Finalize reporting** — What changed and how was it validated?

### When to Use

| Stage | Use Attention Repo? | Why |
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

### 3. Central Control Plane — The Shared State

Lives under `~/.openclaw/attention-repo/`:
- `config.json` — persistent source of truth for registered projects and discovery settings
- `index.json` — derived runtime/status projection for menu rendering and stale-state reporting

Rules:
- Registering a project updates `config.json`
- Reindexing or normal operations refresh `index.json`
- If the two files disagree, `config.json` is authoritative

---

## Command Reference

### Main Menu (Telegram)

Type `/attention_repo` to see:

```
*Attention Repo* — v<current>

Index updated: 2026-03-08
Registered: 2 project(s)

[📋 Projects]  [🔍 Assemble]
[✓ Freshness]  [📝 Status]
[▶️ Declare]   [🏁 Finalize]
```

**Telegram:** Use `/attention_repo` (underscore is canonical)

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
  --description "Menu-first UX with Telegram integration"

# Compile control-plane state after a deployed skill update
attention bootstrap-update

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
| **Command Normalization** | `/attention_repo` → `/attention_repo` both work |
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

**Attention Repo** = Guards architectural intent and tracks state
**Agent Orchestration** = Manages distributed agent swarms

Together they enable **L3+ Operational** multi-agent workflows:

```
River: "Build me a payment system"
  ↓
Brad (Orchestrator)
  ├─ Spawns: ArchitectureAgent
  │   └─ Uses Attention Repo
  │       ├─ declare-intent for payment-api
  │       ├─ register-new-entity E-STRIPE-HOOK
  │       └─ assemble → returns context
  │
  ├─ Spawns: BackendAgent
  │   └─ Uses Attention Repo
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

| AO Feature | Attention Repo Role |
|------------|---------------------|
| **Session spawn** | Each agent calls `declare-intent` before work |
| **Progress tracking** | `update-task` feeds AO status dashboard |
| **Completion** | `finalize-change` generates AO-compatible reports |
| **State persistence** | `~/.openclaw/attention-repo/index.json` survives session restarts |
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

### Central config.json

```json
{
  "$schema": "attention-repo-config-v3",
  "paths": {
    "state_root": "/Users/me/.openclaw/attention-repo",
    "default_scan_roots": [
      "/Users/me/.openclaw/workspace/projects"
    ],
    "optional_scan_roots": {
      "skills": "/Users/me/.openclaw/workspace/skills",
      "plugins": "/Users/me/.openclaw/plugins"
    }
  },
  "projects": {
    "my-api": {
      "canonical_path": "/Users/me/projects/my-api",
      "source_strategy": "local_only",
      "scope": "projects",
      "menu_visible": true
    },
    "my-frontend": {
      "canonical_path": "/Users/me/projects/my-frontend",
      "source_strategy": "local_only",
      "scope": "projects",
      "menu_visible": true
    }
  }
}
```

---

## Maturity Levels

### L1 Prototype (No Attention Repo)
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
Add to `~/.openclaw/attention-repo/config.json`:
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
- Try both `/attention_repo` and `/attention_repo`

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

1. Fork `openclaw/attention_repo`
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
