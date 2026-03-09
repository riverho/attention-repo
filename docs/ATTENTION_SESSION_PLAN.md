# Attention Session Plan

## Problem
Humans and LLMs do not hold working context the same way.

- Humans switch goals, revisit prior work, and often resume from partial memory.
- LLMs perform best when the current objective, recent state, constraints, and architectural context are explicit.
- Chat history is not a reliable working-memory system for multi-repo work.
- Repo files preserve code, but not always the active focus, reason for change, or wrap-up outcome.

The current attention-layer already solves part of this with `start`, `init`, `wrap`, repo-local files, and a central index. The next step is to promote the workflow from command-level state to an explicit **attention session** model.

## Product Thesis
Attention Layer should become the shared working-memory layer between a human operator and one or more LLM sessions.

The product is not “a command set.” The product is:

- a way to enter focus on a project,
- a way to preserve the current reasoning state,
- a way to close work with a durable wrap-up,
- and a way to resume later without rescanning everything.

## First-Class Object: Attention Session
Each active work thread should map to one session.

Suggested fields:

- `session_id`
- `project`
- `status`: `active | paused | blocked | wrapped`
- `declared_goal`
- `current_task`
- `task_summary`
- `architectural_intent`
- `affected_entities`
- `blockers`
- `last_human_update`
- `last_llm_update`
- `wrap_summary`
- `started_at`
- `updated_at`
- `wrapped_at`

## Memory Boundaries
Keep the split explicit.

### Repo-local memory
Lives with the project:

- `!MAP.md`
- `CURRENT_TASK.md`
- `.attention/architectural_intent.json`
- `.attention/map_freshness.json`
- `.attention/ATTENTION_FINALIZE.md`
- future: `.attention/session.json`

Purpose:
- durable project context
- git-visible operational memory
- architecture and task state close to code

### Central control-plane memory
Lives under `~/.openclaw/attention-layer/`:

- `config.json`
- `index.json`
- future: `sessions/`

Purpose:
- fast menu rendering
- cross-project status
- lightweight routing metadata
- session lookup without repo scanning

## User Surface
User-facing workflow should stay minimal:

- `start <project> [task]`
- `init`
- `wrap <project>`

Meaning:

- `start` opens or resumes an attention session and shows latest task context first
- `init` discovers projects and backfills required templates
- `wrap` performs freshness, reflection, finalize, and sync

Telegram remains the primary guided UI:

- `Projects`
- `Index New`
- `Wrap Up`

## Agent Orchestrator Synergy
`agent-orchestrator` should integrate as a session producer and updater, not as a second source of truth.

Current AO signals:

- OpenClaw session lifecycle
- multi-agent task orchestration
- attention bridge outputs
- event and state projections

Recommended contract:

1. AO starts work on a repo:
   - AO calls attention-layer `start <project> <task>`
   - attention-layer opens or updates the attention session

2. AO spawns sub-agents:
   - AO attaches session metadata to each agent run
   - attention-layer records task and status projections only

3. AO completes a work phase:
   - AO writes summary/blocker/result into the active session
   - attention-layer updates repo-local and central state

4. AO closes work:
   - AO calls attention-layer `wrap <project>`
   - attention-layer writes finalize, freshness, sync, and wrap summary

Design rule:
- AO owns execution orchestration
- attention-layer owns human/LLM shared attention memory

## Phased Plan

### Phase 1: Session Schema
- Define `attention session` JSON schema
- Add central session registry under `~/.openclaw/attention-layer/sessions/`
- Add repo-local `.attention/session.json`
- Keep one active session per project first

### Phase 2: Start/Resume Semantics
- `start <project>` opens or resumes the session
- show latest task, blockers, and last wrap summary
- next free-text reply updates `current_task`

### Phase 3: Wrap Semantics
- `wrap <project>` writes:
  - freshness result
  - finalize report
  - wrap summary
  - updated central session/index metadata
- optionally mark `CURRENT_TASK.md` as wrapped or paused

### Phase 4: AO Integration
- define AO -> attention-layer update contract
- accept AO session IDs and task IDs
- store AO session references inside attention session state
- keep attention-layer rebuildable even if AO is offline

### Phase 5: Reflection as First-Class Memory
- add explicit `reflection` or `wrap_summary` artifact
- make reflection queryable in Telegram and CLI
- support “what changed since last wrap?” without rescanning the repo

## Success Criteria
- A user can return to a project and understand the active context in under 10 seconds.
- Telegram and CLI expose the same mental model.
- AO can project multi-agent progress into the same session state.
- Normal menu rendering never needs full workspace scans.
- Wrap-up produces durable memory, not just command output.

## Risks
- Too many memory files without one canonical session object
- AO and attention-layer diverging into separate state models
- over-automation that mutates repos on passive startup
- storing verbose summaries that increase token cost without improving recall

## Immediate Next Moves
1. Add `.attention/session.json` and central `sessions/` support.
2. Change `start` to create/resume a session instead of only updating `CURRENT_TASK.md`.
3. Add a dedicated wrap summary artifact.
4. Define the AO integration payload and event mapping.
