# Attention Repo

*Deployment intelligence for coding agents.*

Implementation repo status:

- canonical product and launch spec lives in [docs/MASTER_SPEC_HANDOFF.md](/Users/river/.openclaw/workspace/projects/attention-repo/docs/MASTER_SPEC_HANDOFF.md)
- canonical product design source lives in [/Users/river/.openclaw/workspace/notes/attention-repo/MASTER_DESIGN_AND_IMPLEMENTATION.md](/Users/river/.openclaw/workspace/notes/attention-repo/MASTER_DESIGN_AND_IMPLEMENTATION.md)
- this repo is the implementation surface, not the authoritative launch messaging doc
- the OSS-local package boundary is documented in [docs/OSS_LOCAL_BOUNDARY.md](/Users/river/.openclaw/workspace/projects/attention-repo/docs/OSS_LOCAL_BOUNDARY.md)

Your coding agent can read code.
It still cannot reliably see deployment boundaries.

Attention Repo helps agents understand:
- what deployable surface owns a file
- what CI/CD pipeline owns a change
- whether a task crosses service boundaries
- what architectural and runtime context should be in scope before editing

It is not another planning system.
It gives agents repo and deployment intelligence they cannot reliably infer from code alone.

---

## The problem

Modern coding agents can:
- inspect files
- trace symbols
- edit code
- run tests
- ship real changes

But they still often miss repo-level reality:
- two folders may deploy through different pipelines
- one service may be out of scope for the current task
- a seemingly simple edit may cross a deployment boundary
- a PR may touch multiple deployable surfaces without anyone noticing early enough

That leads to expensive stupidity:
- wrong service touched
- wrong pipeline assumed
- hidden cross-boundary edits
- deployment breakage
- poor auditability for AI-generated changes

Attention Repo exists to close that gap.

---

## What Attention Repo does

### Today
The current implementation provides boundary awareness mainly through:
- manual entity mapping in `!MAP.md`
- intent declaration against known entities
- deployment-pipeline validation
- scoped context assembly
- freshness checks and finalize reports

In practice, that means the system can already help answer:
- which declared entity is in scope
- which pipeline should apply to the task
- whether the declared work mismatches the mapped boundary
- what repo and CI/CD context should be injected into the work session

### Coming next
The target launch contract is:
- Bun package for installation
- local `attention-repo setup --key`
- local `attention-repo status`
- packaged local MCP runtime
- v2 orchestration-complete MCP tools
- Attention Lab key handoff into local setup

### What stays constant
Whether manual or discovered, the core value is the same:
- boundary awareness
- scoped context
- boundary validation
- audit trail

---

## What it is not

Attention Repo is **not** primarily:
- a generic task planner
- a replacement for agent memory
- a broad AI governance suite
- a generic architecture documentation tool

Coding agents already have planning systems.
Attention Repo works with those systems by supplying deployment-aware repo context.

---

## Why now

Three things changed:

1. **Agents now have direct filesystem and execution access**
   The blast radius is real.

2. **Agents are already good at planning**
   Cursor, Claude Code, Devin, Kiro, Amp and others already plan, reflect, and verify.
   The missing layer is deployment awareness.

3. **Multi-service software is normal**
   More teams now have multiple deployable surfaces than their agents can reliably model.

---

## Launch wedge

The wedge is simple:

**Before an agent edits code, it should know what deployable surface it is touching.**

That means Attention Repo should answer questions like:
- What pipeline owns `src/tasks/routes.ts`?
- Does this task cross a service boundary?
- Which files are in scope for this deployable surface?
- What repo context should the agent see before changing this code?

---

## Current launch direction

The open-source launch path is no longer active.

The current launch critical path is:

1. Bun package
2. working `attention-repo setup --key`
3. working `attention-repo status`
4. packaged local MCP runtime
5. demo repo
6. public README and side-by-side proof

Attention Lab is the human onboarding and key-distribution layer.
The local MCP runtime is the agent integration layer.

## Installation

The official install surface is a single package:

```bash
bun install -g @summon-ai/attention-repo
attention-repo setup --key "ak_attention_repo_xxx"
attention-repo status
```

The same package owns the local MCP runtime:

```bash
attention-repo tools
attention-repo mcp-config
attention-repo mcp
```

That means the next user does not need to discover or install a second MCP package.
The root package is the release artifact.
The bundled MCP runtime is an internal implementation detail.

---

## MCP target

The launch target is the v2 orchestration-complete MCP surface:

1. `attention_resolve_scope`
2. `attention_get_constraints`
3. `attention_declare_scope`
4. `attention_assemble_context`
5. `attention_validate_changes`
6. `attention_finalize_audit`

The current codebase still contains earlier MCP tool names in places.
Those are transitional implementation details, not the long-term contract.

The tool registry shipped with the package is queryable locally:

```bash
attention-repo tools
attention-repo tools --json
```

And the package can print a ready-to-paste MCP config snippet:

```bash
attention-repo mcp-config
attention-repo mcp-config codex
```

---

## Who this is for

### Primary users
Teams that:
- already use coding agents
- work in multi-service production repos
- already have CI/CD pipelines
- feel real pain from architecturally naive agent edits

Ideal shape:
- 5 to 50 engineers
- startup or mid-market product team
- at least 2 meaningful deployment boundaries

### Secondary users
- fintech / healthcare / regulated teams
- platform engineering teams
- teams that need traceability for AI-generated changes

### Not the best fit yet
- toy single-service apps
- teams not using coding agents
- teams shopping for a broad enterprise governance platform before they have concrete boundary pain

---

## Competitive position

Current coding agents already do a lot well:
- planning
- reflection
- task tracking
- memory / steering files
- post-edit verification

That is not the gap.

The gap is:
- deployment awareness
- cross-boundary validation
- structured post-change audit trail

That is where Attention Repo lives.

---

## Quick example

A coding agent is asked to update a task API route.

Without repo intelligence, it may:
- edit files in the wrong service
- assume the wrong deployment pipeline
- drag another deployable surface into scope

With today’s Attention Repo workflow, the agent or operator declares the relevant entity and pipeline first, then assembles scoped context before editing.

With the stronger product direction, Attention Repo should increasingly infer and answer this directly, for example:
- this file belongs to `tasks-service`
- it deploys through `api-deploy.yml`
- notifications are out of scope
- changes crossing into `notifications-service` require separate handling

That is the product value in one move.

---

## Current workflow support

Attention Repo also includes a workflow layer for teams that want stricter operational discipline.

That layer includes:
- intent declaration
- current task tracking
- map freshness checks
- finalize reports
- released-attention state

This is useful, especially in more operational or multi-agent environments.
But it is not the main launch story.
The main story is repo and deployment intelligence.

---

## Core workflow commands

If you want the stricter workflow today, the current CLI supports a 4-step flow:

### 1. Declare intent
```bash
scripts/attention declare-intent /path/to/repo \
  --affected-entities E-ATTN-CLI-01 \
  --deployment-pipeline .github/workflows/ci.yml \
  --first-principle-summary "Routes validated input into deterministic command execution." \
  --requires-new-entity false
```

### 2. Assemble context
```bash
scripts/attention assemble /path/to/repo
```

### 3. Update task status
```bash
scripts/attention update-task /path/to/repo \
  --status-markdown "Mapped entity and pipeline. Applying changes now."
```

### 4. Finalize change
```bash
scripts/attention finalize-change /path/to/repo \
  --tests-command "scripts/attention --help" \
  --tests-result pass \
  --notes "Ready for review"
```

This workflow is best understood as an advanced operating mode on top of the repo-intelligence core.

---

## Current repo artifacts

Today Attention Repo uses a few core files:

- `!MAP.md` — architecture map and entity registry
- `CURRENT_TASK.md` — current task state
- `.attention/` — local runtime state
- `~/.openclaw/attention-repo/config.json` — central control-plane config
- `~/.openclaw/attention-repo/index.json` — derived runtime index

These support the current implementation and workflow model.

---

## Near-term roadmap

1. package the CLI for Bun release
2. implement `attention-repo setup --key`
3. implement `attention-repo status`
4. package the local MCP runtime for `bunx`
5. move MCP implementation toward the v2 tool surface
6. build the demo repo and side-by-side proof

---

## What must be proven

The key product test is simple:

**Do agents with Attention Repo make fewer wrong-boundary edits than agents using plain context files?**

If yes, the product is real.
If not, it is just an elegant extra layer.

---

## Install and current usage

### Current implementation setup
```bash
cd ~/.openclaw/workspace/projects/attention-repo
```

### Initialize shared control-plane config
```bash
scripts/attention init-config
```

### Discover and register repos
```bash
scripts/attention init --dry-run
scripts/attention init
scripts/attention reindex
```

### Start using the current workflow
```bash
/attention_repo
/attention_repo assemble my-project
```

Canonical version metadata lives in [`version.json`](./version.json).

The canonical product and launch contract is documented in:

- [docs/MASTER_SPEC_HANDOFF.md](/Users/river/.openclaw/workspace/projects/attention-repo/docs/MASTER_SPEC_HANDOFF.md)

---

## Archived legacy integrations

Older skill/OpenClaw/Telegram integration files are archived out of the OSS-local package boundary.

The active local-testing surface is:

- Bun CLI
- local MCP
- local workflow scripts
- local tests

Archive reference:

- [docs/OSS_LOCAL_BOUNDARY.md](/Users/river/.openclaw/workspace/projects/attention-repo/docs/OSS_LOCAL_BOUNDARY.md)
