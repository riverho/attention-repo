# Case Chart Generation

## Purpose

Generate stable, publishable benchmark charts from case artifacts.

Inputs:
- `protocol.md`
- `raw-results.tsv`
- `summary.json`

Outputs:
- `charts/before-after-bar.svg`
- `charts/error-rate-bar.svg`
- `charts/progression-line.svg`
- `charts/manifest.json`

## Script

Use:

`[generate_case_charts.py](/Users/river/.openclaw/workspace/projects/attention-repo/scripts/generate_case_charts.py)`

And before chart generation, summarize raw results with:

`[summarize_case_results.py](/Users/river/.openclaw/workspace/projects/attention-repo/scripts/summarize_case_results.py)`

## Usage

From the repo root:

```bash
python3 scripts/summarize_case_results.py docs/cases/autoresearch-intent-gate
python3 scripts/generate_case_charts.py docs/cases/autoresearch-intent-gate
```

The script creates a `charts/` folder inside the case directory if it does not already exist.

## What The Charts Mean

### `before-after-bar.svg`

Primary control-vs-treatment comparison.

Default priority:
1. `retained_improvement_rate`
2. `best_achieved_val_bpb`
3. `invalid_edit_rate`
4. `crash_rate`

### `error-rate-bar.svg`

Focused comparison of invalid edit rate across conditions.

### `progression-line.svg`

Best-so-far retained primary metric over run index, split by condition.

For `val_bpb` and loss-like metrics, lower is treated as better.

## Data Rules

- If `summary.json` does not yet contain values, bar charts render a no-data state.
- If `raw-results.tsv` has no completed runs, the progression chart renders a no-data state.
- Whitepapers and website pages should use generated charts, not manually redrawn copies.

## Publication Rule

Do not publish a chart that is not traceable back to:

1. `raw-results.tsv`
2. `summary.json`
3. the case protocol
