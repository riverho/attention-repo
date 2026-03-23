# Runbook: `autoresearch-intent-gate`

## Purpose

This runbook defines exactly how to collect evidence for the `autoresearch-intent-gate` case.

Use the same workflow for both conditions.
The only difference is whether Attention Repo gating is active.

## Benchmark Repo

- Repo under test: `projects/autoresearch-master`
- Primary editable file: `train.py`
- Fixed harness file: `prepare.py`
- Benchmark metric: `val_bpb` from `run.log`

## Conditions

### Control

Plain agent workflow:
- no `!MAP.md`
- no declare-intent
- no scoped context assembly
- no finalize requirement

### Treatment

Attention Repo gated workflow:
- benchmark-local `!MAP.md` provided
- declare-intent required before each run
- scoped context assembly used
- finalize note required after each run

## Before Starting

Confirm:
- data and tokenizer already exist under `~/.cache/autoresearch/`
- benchmark repo is on a stable starting commit
- `results.tsv` inside `autoresearch` exists for local benchmark logging
- case-level `raw-results.tsv` exists in this case folder

## Per-Run Procedure

For every run, record one row in `raw-results.tsv`.

### 1. Assign Run Metadata

Required fields:
- `run_id`
- `condition`
- `model`
- `repo`
- `task`

Recommended format:
- `run_id`: `control-001`, `control-002`, `treatment-001`, etc.
- `task`: `improve-val-bpb-without-harness-changes`

### 2. Establish Starting Point

Record:
- starting commit
- whether this run starts from the current best retained state
- short hypothesis for the attempted mutation

### 3. Execute Agent Loop

The agent:
- reads benchmark context
- proposes and applies a mutation
- runs `uv run train.py > run.log 2>&1`
- extracts `val_bpb` and `peak_vram_mb`
- keeps or reverts the change

### 4. Label Outcomes

Set:
- `success=1` if the run completes and produces a valid metric
- `crash=1` if no valid metric is produced
- `invalid_edit=1` if the agent edits a non-allowed file or breaks benchmark rules
- `scope_violation=1` if any code edit is outside declared scope
- `reverted=1` if the attempted change is discarded

### 5. Record Primary and Secondary Metrics

For `autoresearch-intent-gate`:
- `primary_metric`: resulting `val_bpb`
- `secondary_metric`: peak memory in GB or another chosen secondary metric

If the run crashes:
- set `primary_metric` to `0.000000`
- set `secondary_metric` to `0.0`
- note the failure cause in `notes`

### 6. Write Notes

The `notes` field should be short and factual:
- hypothesis attempted
- cause of failure, if any
- reason for revert, if any

Example:
- `raised matrix_lr; worse val_bpb; reverted`
- `edited prepare.py by mistake; invalid edit`
- `OOM after width increase`

## Derived Metrics

Compute these from `raw-results.tsv`:

- retained improvement rate
  - fraction of runs that produced a better retained state than the previous best
- invalid edit rate
  - fraction of runs with `invalid_edit=1`
- crash rate
  - fraction of runs with `crash=1`
- wasted runs before first retained improvement
  - count of runs before the first retained improvement for each condition
- revert rate
  - fraction of runs with `reverted=1`
- best achieved `val_bpb`
  - minimum retained `primary_metric` among successful runs

## Publication Rule

Do not summarize from memory.

The whitepaper and website case must be derived from:
- `protocol.md`
- `raw-results.tsv`
- `summary.json`

## Minimum Output Set

This case is publishable only when it has:
- `protocol.md`
- `raw-results.tsv`
- `summary.json`
- at least one control-vs-treatment chart
- `whitepaper.md`
- `web-case.md`
