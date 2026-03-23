# Attention Repo Benchmark Case Roadmap

## Goal

Build a publishable evidence pipeline for Attention Repo.

Each case should end in:
- a protocol
- raw results
- charts
- a whitepaper
- a website-ready case page

## Phase 1: Fast Proof With `autoresearch`

### Case 1: `autoresearch-intent-gate`

Claim:
- intent declaration and scoped context improve autonomous experiment quality

Why first:
- fastest measurable case
- cheap to rerun
- easy control/treatment setup

Primary outputs:
- crash-rate bar chart
- improvement-rate bar chart
- whitepaper on gated execution quality

### Case 2: `autoresearch-scope-discipline`

Claim:
- explicit allowed-file scope reduces invalid edits and wasted loops

Why second:
- uses the same benchmark repo
- tests a narrower product capability

Primary outputs:
- invalid-edit-rate bar chart
- wasted-runs-before-improvement comparison

## Phase 2: Core Wedge Proof With Multi-Surface Benchmarks

### Case 3: `monorepo-boundary-detection`

Claim:
- Attention Repo improves boundary and pipeline resolution accuracy

Primary outputs:
- resolution-accuracy bar chart
- confidence calibration comparison

### Case 4: `monorepo-cross-pipeline-rejection`

Claim:
- Attention Repo rejects cross-pipeline intent mismatches before risky execution

Primary outputs:
- prevented wrong-boundary edits chart
- rejection precision/recall summary

### Case 5: `monorepo-scoped-context-vs-plain-context`

Claim:
- deployment-aware context reduces wrong assumptions in complex repos

Primary outputs:
- wrong-pipeline-assumption bar chart
- task-quality comparison

## Phase 3: Website Packaging

Once the first two cases are complete:

1. publish the whitepapers
2. create a benchmark/cases section on the website
3. add one visual summary card per case
4. link each card to the full whitepaper

## Publishing Rule

Do not publish a case if the evidence is only qualitative.

Attention Repo needs cases that are:
- measurable
- reproducible
- honest about limitations
