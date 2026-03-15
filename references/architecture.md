# Attention-repo v0.3.0 Architecture

## Objective
Implement a strict OODA loop with CI/CD entity mapping as a write gate.

## Core Components
- `!MAP.md`
- `CURRENT_TASK.md`
- `scripts/jit-context.py`
- `scripts/attention`

## OODA Flow
1. Observe: read `!MAP.md`, task, git state.
2. Orient: `declare-intent` validates entities + pipeline.
3. Decide: assemble context with CI/CD and runtime file injection.
4. Act: edit/test, then finalize with deterministic report.

## Non-Goals
- Background scanning
- Multi-agent funnel chaining
- Free-form architecture hallucination
