# Attention Repo Case Factory

## Purpose

Turn benchmark runs into publishable evidence for Attention Repo.

This system should produce the same output shape every time:

1. benchmark protocol
2. raw results
3. summary metrics
4. charts
5. whitepaper
6. short website case page

The goal is not more internal notes. The goal is repeatable product proof.

## Evidence Families

Attention Repo needs two case families.

### Family A: Execution Discipline Cases

Use these to prove that explicit gating improves agent behavior.

Good benchmark environments:
- `projects/autoresearch-master`
- other single-surface or narrow-surface repos

These cases validate claims such as:
- intent declaration reduces invalid edits
- scoped context reduces crash rate
- gated agents waste fewer runs
- audit and finalize flows improve reproducibility

These cases are strong for:
- discipline
- execution quality
- auditability
- repeatability

These cases are weak for:
- real multi-service boundary intelligence
- file-to-pipeline inference in complex repos

### Family B: Boundary Intelligence Cases

Use these to prove the launch wedge:

> Before an agent edits code, it should know what deployable surface it is touching.

Good benchmark environments:
- synthetic multi-service monorepo
- real multi-surface internal repo

These cases validate claims such as:
- Attention Repo prevents wrong-boundary edits
- file-to-entity-to-pipeline resolution improves decisions
- cross-pipeline conflicts are caught before code changes ship

These cases are strong for:
- deployment awareness
- cross-boundary protection
- CI/CD validation
- launch messaging

## Benchmark Conditions

Every case should compare a control and a treatment.

### Control

Plain agent workflow.

Typical shape:
- repo files only
- default coding-agent planning
- no `!MAP.md` gate
- no mandatory declare-intent
- no scoped context assembly

### Treatment

Attention Repo gated workflow.

Typical shape:
- `!MAP.md` available
- mandatory declare-intent
- scoped context assembly
- freshness check or equivalent guard
- finalize report required

If the treatment is different in a case, write the exact deviation in the protocol.

## Standard Artifacts

Each case should live in its own folder:

```text
cases/<case-slug>/
├── protocol.md
├── raw-results.tsv
├── summary.json
├── charts/
│   ├── before-after-bar.svg
│   └── metric-trend.svg
├── whitepaper.md
├── web-case.md
└── assets/
    └── hero.png
```

### Required Files

#### `protocol.md`

Declares:
- problem
- hypothesis
- benchmark repo
- model/runtime
- control condition
- treatment condition
- run count
- primary metrics
- stop conditions
- threats to validity

#### `raw-results.tsv`

One row per run.

Minimum columns:

```text
run_id	condition	model	repo	task	success	crash	scope_violation	invalid_edit	reverted	primary_metric	secondary_metric	duration_seconds	notes
```

Example interpretation:
- `primary_metric` may be `val_bpb`, task success rate, or score
- `secondary_metric` may be memory use, wall clock, or review score

#### `summary.json`

Aggregated metrics for charts and page generation.

Minimum keys:
- case_slug
- benchmark
- control
- treatment
- delta
- key_findings
- limitations

#### `whitepaper.md`

Long-form evidence artifact.

Audience:
- technical buyers
- skeptical engineers
- investors or partners doing diligence

#### `web-case.md`

Shorter publishable case page for the website.

Audience:
- product visitors
- social traffic
- launch readers

## Chart Rules

Keep charts simple and stable across cases.

Use:
- bar chart for control vs treatment
- line chart for progression over runs
- stacked bar only when showing outcome composition

Avoid:
- radar charts
- decorative charts
- 3D charts
- dashboards with ten metrics at once

Recommended default charts:

1. `before-after-bar`
   - control vs treatment on the primary claim
2. `error-rate-bar`
   - crash rate, invalid edit rate, or wrong-boundary rate
3. `progression-line`
   - best-so-far result by run index

## Whitepaper Standard

Every whitepaper should use the same structure:

1. Abstract
2. Problem
3. Hypothesis
4. Benchmark Setup
5. Conditions
6. Measurement Method
7. Results
8. Interpretation
9. Limitations
10. Product Implication

The whitepaper is not a blog post. It is evidence packaging.

## Website Case Standard

Every website case should be compressed:

1. one-line claim
2. benchmark setup in 2 to 3 lines
3. one primary chart
4. three findings
5. one limitations line
6. CTA to full whitepaper

The website case should never oversell what the benchmark did not prove.

## First Five Cases

### 1. `autoresearch-intent-gate`

Claim:
- intent declaration and scoped context improve autonomous research execution quality

Benchmark:
- `projects/autoresearch-master`

Primary metrics:
- improvement rate
- crash rate
- off-scope edit attempts

### 2. `autoresearch-scope-discipline`

Claim:
- explicit edit-scope rules reduce invalid file touches and wasted runs

Benchmark:
- `projects/autoresearch-master`

Primary metrics:
- invalid edit rate
- reverted run rate
- wasted runs before first valid improvement

### 3. `monorepo-boundary-detection`

Claim:
- Attention Repo improves file-to-entity-to-pipeline resolution accuracy

Benchmark:
- synthetic multi-service repo

Primary metrics:
- boundary resolution accuracy
- confidence calibration

### 4. `monorepo-cross-pipeline-rejection`

Claim:
- Attention Repo catches cross-pipeline intent mismatches before execution

Benchmark:
- synthetic multi-service repo

Primary metrics:
- rejection precision
- rejection recall
- prevented wrong-boundary edits

### 5. `monorepo-scoped-context-vs-plain-context`

Claim:
- scoped deployment-aware context reduces wrong assumptions in multi-surface repos

Benchmark:
- synthetic or real internal multi-service repo

Primary metrics:
- wrong-boundary edit rate
- wrong-pipeline assumption rate
- task completion quality

## Recommended Build Order

1. `autoresearch-intent-gate`
2. `autoresearch-scope-discipline`
3. `monorepo-boundary-detection`
4. `monorepo-cross-pipeline-rejection`
5. `monorepo-scoped-context-vs-plain-context`

Start with `autoresearch` because it is the fastest way to produce measurable evidence.
Then move to monorepo cases because they validate the core launch wedge.

## Operating Rule

Do not publish a case unless all three are true:

1. the protocol is explicit
2. the raw results are preserved
3. the case states its limits honestly

Attention Repo needs credible evidence, not content marketing theater.
