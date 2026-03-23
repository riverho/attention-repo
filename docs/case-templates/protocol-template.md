# Protocol Template

## Case

- Case Slug:
- Evidence Family:
- Status: draft | running | complete | published

## Claim

One sentence only.

Example:

`Attention Repo reduced invalid off-scope edits in autonomous model experiments.`

## Problem

What agent failure mode is being tested?

## Hypothesis

If the treatment condition includes Attention Repo gates, the agent should outperform the control on the defined metrics.

## Benchmark Environment

- Repo:
- Commit / snapshot:
- Benchmark type:
- Runtime:
- Model:
- Time budget per run:
- Total planned runs:

## Conditions

### Control

Describe exactly what the agent sees and what is allowed.

### Treatment

Describe exactly which Attention Repo capabilities are active.

Required details:
- `!MAP.md` present or absent
- declare-intent required or not
- scoped context used or not
- freshness/finalize enforced or not

## Task

What the agent is asked to do.

Keep the task wording fixed across conditions.

## Primary Metrics

- Metric 1:
- Metric 2:

## Secondary Metrics

- Metric 1:
- Metric 2:

## Failure Rules

Define what counts as:
- crash
- invalid edit
- scope violation
- wrong-boundary action
- forced revert

## Stop Conditions

When does the case stop early?

Examples:
- benchmark instability
- repeated infrastructure failure
- protocol violation

## Threats To Validity

List known limits before running the case.

## Publication Rule

This case may be published only if:
- raw results are retained
- summary metrics are reproducible
- the whitepaper includes limits honestly
