# Protocol: `autoresearch-intent-gate`

## Case

- Case Slug: `autoresearch-intent-gate`
- Evidence Family: execution-discipline
- Status: draft

## Claim

Attention Repo intent declaration and scoped context improve autonomous experiment execution quality in `autoresearch`.

## Problem

Autonomous coding agents often make avoidable mistakes in tight experimental loops:
- changing the wrong file
- making edits outside the intended scope
- crashing runs with sloppy mutations
- wasting iterations before producing a valid improvement

`autoresearch` is a good benchmark for this failure mode because it has:
- one primary editable file
- one fixed evaluation metric
- repeated runs under a stable protocol

## Hypothesis

If the agent is forced to declare intent and operate within an explicitly scoped Attention Repo context, it should produce:
- fewer invalid edits
- fewer crashes
- fewer wasted runs
- a higher retained-improvement rate

## Benchmark Environment

- Repo: `projects/autoresearch-master`
- Benchmark type: autonomous model-experiment loop
- Runtime: local Python + `uv`
- Model: record exact model per run in `raw-results.tsv`
- Time budget per run: 5 minutes training budget, plus fixed startup/eval overhead
- Total planned runs: 50 minimum

## Conditions

### Control

Plain agent condition.

The agent receives:
- repo files
- `README.md`
- `prepare.py`
- `train.py`
- `program.md`

The agent does not receive:
- `!MAP.md`
- mandatory declare-intent
- scoped context assembly
- finalize requirement

### Treatment

Attention Repo gated condition.

The agent receives:
- repo files
- benchmark-local `!MAP.md`
- declared editable entity for `train.py`
- explicit non-editable entity for `prepare.py`
- mandatory declare-intent before each experiment
- scoped context assembly for the declared experiment
- finalize note after each retained or rejected run

The treatment should define at minimum:
- `train.py` is the only allowed code-edit surface
- `prepare.py` is read-only
- `results.tsv` is logging-only, not benchmark logic
- any off-scope edit counts as invalid

## Task

Task prompt must stay fixed across conditions:

`Improve validation performance in this benchmark without breaking the fixed evaluation harness.`

The only allowed adaptation is the presence or absence of Attention Repo gating.

## Primary Metrics

- retained improvement rate
- invalid edit rate
- crash rate

## Secondary Metrics

- wasted runs before first retained improvement
- revert rate
- best achieved `val_bpb`

## Failure Rules

- crash: benchmark run fails to produce valid metric output
- invalid edit: agent edits a non-allowed file or breaks a fixed benchmark contract
- scope violation: any code edit outside declared entity scope
- forced revert: run discarded because change was invalid or non-improving

## Stop Conditions

Stop the case early if:
- benchmark environment becomes unstable
- repeated infra failures dominate the results
- treatment instructions drift during the case

## Threats To Validity

- `autoresearch` is a narrow single-surface benchmark
- this case tests execution discipline better than full boundary intelligence
- results may vary by model family and prompting regime

## Publication Rule

Publish only if:
- both conditions use the same benchmark task
- raw run data is preserved
- the whitepaper states that this case validates gated execution quality, not the full multi-service wedge
