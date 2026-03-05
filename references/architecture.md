# Architecture — Two-Layer Context Pattern

## Core Design

```
┌─────────────────────────────────────────────────────────┐
│ LAYER 1: Human Surface                                  │
├─────────────────────────────────────────────────────────┤
│ • !MAP.md          → Source of truth (you write)       │
│ • !CONNECTIONS.md  → Shared understanding (co-edit)    │
│ • TLDR.md          → Compressed current state          │
│ • Human            → Gatekeeper, approver, director    │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼ Hardcoded gate
┌─────────────────────────────────────────────────────────┐
│ LAYER 2: Agent Substrate                                │
├─────────────────────────────────────────────────────────┤
│ • Search Agent     → Filter 99% of noise               │
│ • Planner Agent    → Find leverage points              │
│ • Synthesis Agent  → Propose options                   │
│ • State Manager    → Persist context between sessions  │
└─────────────────────────────────────────────────────────┘
```

## Key Principles

### 1. Discard Aggressively

The human brain does this naturally — you forget most of what you read. LLMs don't unless forced.

**Discard triggers:**
- Older than N days (default: 30)
- Not referenced in last 5 sessions
- Marked as "archive" or "old" in !MAP.md
- Fails the "so what?" test (doesn't change next action)

### 2. Transparency, Not Automation

Show the work:
```
Scanning...          → 50 files found
Filtering...         → 3 candidates remain
Analyzing...         → 1 leverage point identified
Proposing...         → 2 options for your review
```

### 3. Hardcoded Human Gate

**Rule:** Before any agent action on a project:
1. Read `!MAP.md`
2. If it doesn't exist → ASK, don't proceed
3. Read `!CONNECTIONS.md` if it exists
4. Only then spawn agents

### 4. Human-Readable Connections

Use markdown tables, not JSON. Both human and AI can read it. Co-edit over time.

## The Three-Layer Funnel

For complex tasks (codebase analysis, multi-step planning):

```
Layer 1: Search        → 50 files → 10 candidates
         ↓ Discard: surface mentions, false positives
Layer 2: Plan          → 10 candidates → 3 leverage points
         ↓ Discard: related but non-essential
Layer 3: Synthesize    → 3 leverage points → 2 options
         ↓ Human gate: you pick 1
```

## Gentle Defaults

- TLDR updates: **manual trigger** (you say "summarize")
- Spawn depth: **2 layers** by default
- Auto-discard: **disabled** until explicitly configured
- Proposals: **always shown** before action

## Communication Style

**Use non-technical metaphors:**
- "Anchors" not "vectors"
- "Bridges" not "edges"  
- "Noise" not "low-similarity results"
- "Paths" not "traversal strategies"

## Session Flow

```
1. Read !MAP.md
2. Read !CONNECTIONS.md (update if needed)
3. Understand intent from human
4. [Optional] Run funnel for complex tasks
5. Surface proposal
6. Wait for human gate
7. Execute or refine
8. Update !CONNECTIONS.md with outcomes
```
