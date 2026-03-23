# Whitepaper Draft: `autoresearch-intent-gate`

## Working Title

Attention Repo Improved Autonomous Experiment Discipline in the `autoresearch` Benchmark

## Abstract

This case compares a plain-agent control condition against an Attention Repo gated treatment condition on the `autoresearch` benchmark. The treatment requires intent declaration and scoped context before each experiment loop. The primary question is whether this gating improves experiment quality by reducing invalid edits, crash rate, and wasted runs, while preserving or improving retained benchmark gains. This case is intended to validate execution-discipline benefits, not full multi-service deployment intelligence.

## 1. Problem

Autonomous coding agents are often good at proposing changes but weak at disciplined repeated execution. In benchmark loops this shows up as invalid edits, wasted experiments, and broken runs.

## 2. Hypothesis

Requiring explicit intent declaration and scoped context should improve execution quality in a repeated autonomous experiment loop.

## 3. Benchmark Setup

- Benchmark repo: `projects/autoresearch-master`
- Primary task: improve `val_bpb` without modifying the evaluation harness
- Control: plain agent workflow
- Treatment: Attention Repo gated workflow
- Planned run count: 50 minimum

## 4. Conditions

### Control

Plain repo context with no Attention Repo gate.

### Treatment

Attention Repo gated loop with declared editable scope and explicit experiment intent.

## 5. Measurement Method

Primary metrics:
- retained improvement rate
- invalid edit rate
- crash rate

Secondary metrics:
- wasted runs before first retained improvement
- revert rate
- best achieved `val_bpb`

## 6. Results

To be filled from `raw-results.tsv` and `summary.json`.

## 7. Interpretation

This section should distinguish measured outcome from inference. If the treatment performs better, the interpretation should focus on whether the gate improved discipline, not whether it made the model architecture itself better.

## 8. Limits

This case does not prove full deployment-boundary intelligence. It is a single-surface benchmark designed to test disciplined autonomous execution.

## 9. Product Implication

If positive, this case supports the claim that Attention Repo improves agent execution quality by forcing explicit scope and intent before edits begin.

## 10. Reproducibility

To be filled with:
- protocol path
- raw results path
- summary path
- chart path
