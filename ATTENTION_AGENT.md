# Attention Agent — Self-Managing Ecosystem

**Date:** 2026-03-01  
**Status:** ✅ OPERATIONAL  

---

## What Is Attention Agent?

The attention-layer **as a true agent** — not just a tool for humans, but an autonomous system that:

1. **Scans** the entire project ecosystem
2. **Evaluates** health of each project
3. **Detects** staleness, conflicts, drift
4. **Auto-organizes** safe actions
5. **Proposes** actions for human approval
6. **Learns** from human decisions

---

## From Tool to Agent

### Before (Tool)
```
Human: "Check ecosystem status"
    ↓
attention list
    ↓
Human: "summon is stale"
    ↓
Human: manually updates TLDR
```

### After (Agent)
```
[Attention Agent — Background Loop]
    ↓
Every hour: Scan ecosystem
    ↓
Detect: "summon stale (7 days)"
    ↓
Auto: Create TLDR update proposal
    ↓
Human notification: "Approve TLDR update?"
    ↓
Human: Y/N
    ↓
Agent: Executes or learns
```

---

## Health Detection

| Health | Criteria | Action |
|--------|----------|--------|
| 🟢 **Active** | Modified < 7 days | Continue monitoring |
| 🟡 **Stale** | Modified 7-30 days | Propose TLDR update |
| 🔴 **Abandoned** | Modified > 30 days | Propose archive |
| ⚠️ **Conflicted** | > 3 active branches | Propose merge |

---

## Commands

```bash
# Scan ecosystem health
attention-agent scan

# Show detailed dashboard
attention-agent status

# Auto-organize (safe actions only)
attention-agent organize

# See proposed actions
attention-agent propose

# Apply proposed action
attention-agent apply <id>

# Full cycle
attention-agent run
```

---

## Current Ecosystem State

```
Ecosystem Health: DEGRADED

Projects: 7
  🟢 Active: 3 (summon, summon-A2A-academy, agent-orchestrator)
  🟡 Stale: 4 (summon-ai-doc, agents-summon-ai, agent_brad, registry-api)
  🔴 Abandoned: 0
  ⚠️  Conflicted: 0
  ❓ Missing TLDR: 3
```

---

## Auto-Actions (No Human Gate)

These execute automatically:

- ✅ **Create missing TLDR.md** — With template
- ✅ **Update !MAP status** — Mark stale projects

## Manual Actions (Human Gate Required)

These require approval:

- 📝 **Update stale TLDR** — Review before changing
- 📦 **Archive abandoned** — Confirm before moving
- 🔀 **Merge branches** — Evaluate before consolidating

---

## Integration with summon Agent

```
summon agent (task-focused)
    └── Manages specific goals (portfolio monitoring)

attention agent (ecosystem-focused)  
    └── Manages all projects, detects drift

Together: Full agent coverage
```

---

## Files

| File | Purpose |
|------|---------|
| `scripts/attention-agent.py` | Python CLI implementation |
| `src/agent.ts` | TypeScript library (for integration) |
| `.attention-state/agent-state.json` | Persistent state |

---

## Architecture

```
┌─────────────────────────────────────────┐
│  Attention Agent                        │
│  ├─ scan_ecosystem()                    │
│  ├─ evaluate_health()                   │
│  ├─ generate_actions()                  │
│  └─ execute_action()                    │
│       ↓                                 │
│  Auto: Safe actions                     │
│  Manual: Human gate                     │
└─────────────────────────────────────────┘
            ↓
    ┌───────┴───────┐
    ▼               ▼
TLDR.md updates   Archive moves
Map updates       Branch merges
```

---

## Status

✅ **Attention Agent Operational**

- Ecosystem scanning: ✅
- Health evaluation: ✅
- Auto-organization: ✅
- Human-gated actions: ✅
- True agent behavior: ✅

**The attention-layer is now a true agent.**

---

*Self-managing ecosystem — 2026-03-01*
