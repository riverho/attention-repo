# Results Schema

## Raw Results TSV

Each case should store per-run results in `raw-results.tsv`.

Minimum schema:

```text
run_id	condition	model	repo	task	success	crash	scope_violation	invalid_edit	reverted	primary_metric	secondary_metric	duration_seconds	notes
```

## Column Definitions

- `run_id`: stable unique run identifier
- `condition`: `control` or `treatment`
- `model`: model/runtime identifier
- `repo`: benchmark repo or fixture name
- `task`: normalized task label
- `success`: `1` or `0`
- `crash`: `1` or `0`
- `scope_violation`: `1` or `0`
- `invalid_edit`: `1` or `0`
- `reverted`: `1` or `0`
- `primary_metric`: benchmark-specific numeric score
- `secondary_metric`: optional secondary numeric score
- `duration_seconds`: wall-clock duration
- `notes`: short free-text note

## Summary JSON

Each case should store aggregate metrics in `summary.json`.

Recommended shape:

```json
{
  "case_slug": "autoresearch-intent-gate",
  "benchmark": "projects/autoresearch-master",
  "run_count": 50,
  "primary_metric_name": "improvement_rate",
  "secondary_metric_name": "crash_rate",
  "control": {
    "improvement_rate": 0.24,
    "crash_rate": 0.18,
    "invalid_edit_rate": 0.12,
    "scope_violation_rate": 0.10
  },
  "treatment": {
    "improvement_rate": 0.38,
    "crash_rate": 0.07,
    "invalid_edit_rate": 0.03,
    "scope_violation_rate": 0.01
  },
  "delta": {
    "improvement_rate": 0.14,
    "crash_rate": -0.11,
    "invalid_edit_rate": -0.09,
    "scope_violation_rate": -0.09
  },
  "key_findings": [
    "Treatment improved the primary metric.",
    "Treatment reduced error rates.",
    "Treatment preserved clearer audit history."
  ],
  "limitations": [
    "Single benchmark environment.",
    "Single model family."
  ]
}
```

## Publication Rule

Do not generate the chart, whitepaper, or webpage from memory alone.

They should all derive from:

1. `protocol.md`
2. `raw-results.tsv`
3. `summary.json`
