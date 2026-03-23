# Whitepaper Template

## Title

Use a factual claim, not a slogan.

Example:

`Attention Repo Reduced Invalid Edits by 43% in an Autonomous Model-Experiment Benchmark`

## Abstract

State:
- benchmark
- control vs treatment
- run count
- primary result
- main limitation

## 1. Problem

Describe the real agent failure mode.

## 2. Hypothesis

State the exact claim tested.

## 3. Benchmark Setup

- benchmark repo
- task definition
- runtime and model
- number of runs
- fixed conditions

## 4. Conditions

### Control

Describe the plain agent setup.

### Treatment

Describe the Attention Repo gated setup.

## 5. Measurement Method

Define:
- primary metrics
- secondary metrics
- how failures are labeled
- how aggregates are calculated

## 6. Results

### Summary Table

Include:
- control mean / rate
- treatment mean / rate
- delta

### Primary Chart

Insert the main comparison chart.

### Secondary Observations

List the most important secondary effects.

## 7. Interpretation

Explain what changed and what likely caused the result.

Keep inference separate from measurement.

## 8. Limits

Be explicit about what this benchmark does not prove.

Examples:
- single-repo benchmark
- synthetic monorepo
- limited run count
- single model family

## 9. Product Implication

Tie the result back to the product surface.

Examples:
- intent declaration
- scoped context assembly
- cross-boundary validation
- finalize / audit chain

## 10. Reproducibility

List:
- protocol path
- raw results path
- summary path
- chart source path

## Appendix

Optional:
- prompt wording
- run logs
- metric formulas
- benchmark notes
