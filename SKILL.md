---
name: attention-layer
description: Manages vivid, dynamic context for human-AI workflows with transparent attention routing and hardcoded human gates. Uses !MAP.md (master) and !MAP_{repo}.md (per-project) naming convention.
---

# Attention Layer

## Overview

This skill manages **vivid context** — the living, breathing state between you and your AI assistant. Uses multi-repo !MAP naming: `!MAP.md` (master) + `!MAP_{repo}.md` (per project).

## Core Principles

1. **Human gate is hardcoded** — Always read !MAP first
2. **Transparency, not automation** — Show the work
3. **Gentle defaults** — Manual triggers
4. **Human-readable connections** — Markdown over JSON

## The Gate Pattern (Multi-Repo)

```
!MAP.md                              ← Master ecosystem map
   ↓
!MAP_{repo}.md                       ← Project-specific context
   ↓
**TLDR.md**                          ← ⭐ DAILY CONTEXT: "What we're doing NOW"
   ↓
!CONNECTIONS_{repo}.md               ← Co-edited session state
   ↓
Agent spawning / Direct execution
```

### Reading the Gate (ALWAYS DO THIS)

```bash
# 1. Read master !MAP (ecosystem overview)
read ~/.openclaw/workspace/projects/!MAP.md

# 2. Read project-specific !MAP (architecture & status)
read ~/.openclaw/workspace/projects/!MAP_{project-name}.md

# 3. Read TLDR.md (⭐ MANDATORY: current focus, blockers, recent decisions)
read ~/.openclaw/workspace/projects/{project-name}/TLDR.md

# 4. Read connections (if exists) — located INSIDE project directory
read ~/.openclaw/workspace/projects/{project-name}/!CONNECTIONS_{project-name}.md
```

**What each file tells you:**
| File | Purpose | Key Info |
|------|---------|----------|
| `!MAP.md` | Ecosystem navigation | What repos exist, how they connect |
| `!MAP_{repo}.md` | Project architecture | Components, status %, phase |
| **`TLDR.md`** | **Daily context** | **What we're doing NOW, last focus, next steps, blockers** |
| `!CONNECTIONS_{repo}.md` | Session state | This conversation's progress |

**Examples:**
- `!MAP_summon.md` — summon runtime (in projects/ root)
- `!MAP_summon-A2A-academy.md` — Factory + conjure (in projects/ root)
- `summon-A2A-academy/TLDR.md` — ⭐ **"Phase 5, 90%, CF-hosted tools next gap"**
- `summon-A2A-academy/!CONNECTIONS_summon-A2A-academy.md` — Session state (inside project dir)

**Key distinction:**
- !MAP files live in `projects/` root (ecosystem-level navigation)
- **TLDR.md lives INSIDE project folder** (daily context, maturity awareness)
- !CONNECTIONS files live INSIDE project folder (project-specific session state)

**⚠️ CRITICAL: TLDR.md is NOT optional.**  
It contains maturity signals: phase, % complete, what's working, what's next.  
Skipping it leads to using demo keys when real auth exists, or building built-in tools when CF-hosted is the architecture.

If TLDR.md doesn't exist, **ask the human** before proceeding.

## Finding the Right Gate

```bash
# List all available !MAPs
ls ~/.openclaw/workspace/projects/!MAP*.md

# Result:
# !MAP.md                      ← Start here (master)
# !MAP_summon.md              ← summon runtime
# !MAP_summon-A2A-academy.md  ← Factory + conjure
```

## What to Extract from TLDR.md

TLDR.md tells you **how to reason** for this repo today:

| Field | What It Means | How It Changes Your Approach |
|-------|---------------|------------------------------|
| **Current Status** | Phase X, Y% complete | 0-30% = explore freely; 85%+ = use real infrastructure |
| **Last Focus** | What just shipped | Don't repeat work already done |
| **Next** | What's actually needed | Build THIS, not something adjacent |
| **Blockers** | What's stuck | Don't assume things work; verify first |

### Maturity-Aware Reasoning (Based on TLDR.md)

**Phase 1-2 (0-60%): Exploration/Architecture**
- Try things, accept rework
- Document decisions in MEMORY.md
- Use demo/placeholder values acceptable

**Phase 3-4 (60-85%): Integration**
- Use existing infrastructure
- Check "Last Focus" to avoid duplication
- Connect components, don't rebuild

**Phase 5+ (85%+): Production**
- ⭐ **Use real keys, real APIs, real auth**
- No demo values allowed
- End-to-end with actual infrastructure

### Example: Reading TLDR.md

```markdown
// summon-A2A-academy/TLDR.md
**Current Status:** Phase 5 Production Hardening, 90% complete
**Last Focus:** Auth system (Resend tested ✅), Security fixes
**Next:** CF-hosted tools (yfinance, sec-filings)
**Blockers:** None
```

**Your reasoning:**
- 90% complete → Use Factory API with real auth, not `demo` keys
- Auth tested ✅ → Keys exist in CF secrets, use them
- CF-hosted tools next → Build Layer 2 (CF Workers), NOT built-in tools
- No blockers → Proceed with confidence

**What NOT to do:**
- ❌ Create isolated example with `OPENAI_API_KEY=demo`
- ❌ Build built-in tool (wrong layer)
- ❌ Skip reading and assume auth doesn't work

## When Human Request ≠ TLDR.md Direction

Sometimes the human asks for something that doesn't match TLDR.md "Next". Handle this carefully:

### Scenario 1: Human clarifies priority shift
```
TLDR.md says: "Next: CF-hosted tools"
Human says: "Fix the auth bug first"
→ TLDR.md is stale. Update it, then proceed with auth bug.
```

### Scenario 2: Human explores adjacent idea
```
TLDR.md says: "Next: CF-hosted tools"
Human says: "What if we used external MCP instead?"
→ This is a **decision point**, not a task. 
→ Discuss architecture (MCP vs CF-hosted), don't just build.
→ Update TLDR.md with the decision before proceeding.
```

### Scenario 3: Human unaware of existing work
```
TLDR.md says: "Auth system tested ✅"
Human says: "Set up Resend for magic links"
→ Gently point to TLDR.md: "Auth is already working, tested today. Want me to show you?"
```

### Rule of Thumb
> If human request contradicts TLDR.md **and** TLDR.md is recent (today/yesterday), **quote TLDR.md** before proceeding.  
> Example: "TLDR.md shows auth is already working (tested today). Should I use the Factory API keys instead of setting up new ones?"

## The Three-Layer Funnel

See `architecture.md` for details.

## Native OpenClaw Integration

The attention-layer skill provides deep integration with OpenClaw via the `attention` CLI wrapper and recognized command patterns.

### Commands

All commands are available via the `attention` script:

```bash
~/.openclaw/workspace/skills/attention-layer/scripts/attention <command> [args]
```

Or via Brad using `/attention` patterns:

| Command | CLI Usage | Brad Pattern | Purpose |
|---------|-----------|--------------|---------|
| **funnel** | `attention funnel "intent" ./project` | `/attention funnel "task" on project` | Run 3-layer attention funnel |
| **check-tldr** | `attention check-tldr ./project` | `/attention check-tldr project` | Validate TLDR.md exists (gate) |
| **read-tldr** | `attention read-tldr ./project` | `/attention read-tldr project` | Display TLDR.md content |
| **init** | `attention init ./project` | `/attention init project` | Create !CONNECTIONS_{repo}.md |
| **read-connections** | `attention read-connections ./project` | `/attention read-connections project` | Read CONNECTIONS file |
| **status** | `attention status ./project` | `/attention status project` | Show funnel state |
| **list** | `attention list` | `/attention list` | List all tracked projects |

### Integration Patterns for Brad

When the human uses these patterns, execute the corresponding command:

**Funnel pattern:**
- User: `/attention funnel "implement auth" on summon-A2A-academy`
- Brad: Execute `attention funnel "implement auth" /path/to/summon-A2A-academy`
- Output: Generated shell script for 3-layer funnel

**Gate check pattern:**
- User: `/attention check-tldr summon`
- Brad: Execute `attention check-tldr /path/to/summon`
- Output: TLDR exists: True/False with path

**Status pattern:**
- User: `/attention status summon-A2A-academy`
- Brad: Execute `attention status /path/to/project`
- Output: Project slug, state file location, layer statuses

**Path Resolution:**
- Map shorthand names (e.g., "summon") to full paths using `~/.openclaw/workspace/projects/`
- If ambiguous, ask: "Which project? summon or summon-A2A-academy?"
- Always resolve to absolute paths before invoking commands

### State Management

Funnel state is stored centrally (not in project folders):

```
~/.openclaw/workspace/.attention-state/
└── {project-name}-{hash}/
    ├── funnel-state.json      # Layer statuses, intent, timestamps
    ├── run-funnel.sh          # Generated executable script
    ├── layer1-search.log      # Layer 1 agent output
    ├── layer2-planner.log     # Layer 2 agent output
    └── layer3-synthesis.log   # Layer 3 agent output
```

This keeps project folders clean while maintaining full state tracking.

## Adaptive Routing /Commands

The % completion model creates a **sunk cost trap** — once TLDR shows high completion, new ideas get rejected. The `/commands` below replace implicit % blocking with **explicit human routing**.

### Core Principle
> Never reject a request based on "we're X% done." Always surface divergence and let the human route.

### Routing Commands

| Command | Brad Pattern | When to Use | Result |
|---------|--------------|-------------|--------|
| `/branch <name>` | `/branch websocket-worker` | New idea deserves its own track | Spawn new attention funnel, create `TLDR_{branch}.md` |
| `/evaluate` | `/evaluate` | Unsure if new idea fits | Run 3-layer funnel → options → human picks |
| `/integrate` | `/integrate` | New idea enhances current stream | Merge into existing TLDR, update Active Focus |
| `/defer <idea>` | `/defer "MCP bridge"` | Good idea, wrong timing | Add to `!MAP.md` "Future" section |
| `/pivot` | `/pivot` | Current stream is wrong | Archive current TLDR, spawn new funnel |
| `/streams` | `/streams` | Check all active workstreams | Show branches, phases, last activity |

### Divergence Detection Flow

When human request doesn't match TLDR "Active Stream":

```
Brad: Divergence detected.

Current:   CF-hosted tools (yfinance ✅)
You asked: "Add real-time WebSocket"

Routing options:
/branch websocket-worker  → Parallel track, own TLDR
/evaluate                 → Analyze fit first
/integrate                → Add to CF-hosted stream
/defer "WebSocket"        → Park for later
/pivot                    → Abandon CF, switch to WebSocket
```

### Implementation for Brad

**Step 1: Check Divergence**
```python
# On every request
read TLDR.md → extract "Active Stream"
if request_topic != Active_Stream:
    divergence = True
```

**Step 2: Surface Options (Never Auto-Reject)**
```
"This diverges from Active Stream: [X]

Options:
/branch   - Start as parallel track
/evaluate - Run 3-layer funnel first
/integrate- Merge into current stream  
/defer    - Park for later
/pivot    - Switch to this entirely

Which one?"
```

**Step 3: Execute Chosen Route**
- `/branch` → `attention funnel "intent" ./project --branch=name`
- `/evaluate` → Run full funnel, present options, wait for pick
- `/integrate` → Update TLDR.md Active Stream, proceed
- `/defer` → Append to `!MAP.md` ## Future section
- `/pivot` → Rename TLDR.md → TLDR_archive_{date}.md, create new TLDR.md

### TLDR.md Format (Updated — No %)

Replace completion % with **Active Stream + Stability Markers**:

```markdown
## TLDR — summon-A2A-academy

**Active Stream:** CF-hosted tools
**Stability:** yfinance deployed ✅, auth hardened ✅
**Open Questions:** MCP vs CF-hosted for external tools?

---

### Adaptive Routing Rules

**If request matches Active Stream:**
→ Proceed with strict mode (real keys, production)

**If request diverges from Active Stream:**
→ Surface /commands, never auto-reject
```

### Comparison: Old vs New

| Situation | Old (with %) | New (with /commands) |
|-----------|--------------|----------------------|
| TLDR says 90%, new idea | LLM resists change | LLM offers `/branch /evaluate /pivot` |
| Parallel experiments | Not supported | `/branch experiment-1`, `/branch experiment-2` |
| Parking ideas | Memory loss | `/defer "idea"` → tracked in !MAP.md |
| True pivots | Awkward | `/pivot` → clean archive + restart |

## Scripts

- `attention` — Main CLI wrapper (native OpenClaw integration)
- `tldr-update.py` — Compress session logs
- `spawn-attention.py` — Generate funnel shell scripts
- `state-manager.py` — Read/write CONNECTIONS and TLDR

## References

- `architecture.md` — Two-layer pattern
- `summon-bridge.md` — sessions_spawn usage
- `connection-template.md` — CONNECTIONS template
