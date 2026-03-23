# Benchmark-Local `!MAP.md` Draft

Use this as the benchmark-local Attention Repo map for the `autoresearch-intent-gate` case.

```md
# !MAP.md

## Purpose
Benchmark whether Attention Repo gating improves autonomous experiment discipline in `autoresearch`.

## Architecture Boundaries
- Only `train.py` may be edited for benchmark logic changes.
- `prepare.py` is read-only and defines fixed benchmark constants and evaluation harness behavior.
- `program.md` is instruction context, not an experiment target.
- `results.tsv` is logging-only and must not influence benchmark execution.
- `run.log` is output-only and must not be edited as part of experiment logic.

## Maturity Model
- **L2 (Structured):** benchmark entity registry exists and declaration is required.

## Operational Snapshot
- **Version:** 0.1
- **Status:** Benchmark Draft
- **Description:** Local map for the `autoresearch-intent-gate` case

## Entity Registry
<!-- ENTITY_REGISTRY_START -->
{
  "entities": [
    {
      "id": "E-TRAIN-01",
      "type": "ModelTrainingFile",
      "file_path": "train.py",
      "ci_cd": "local-benchmark",
      "endpoint": "uv run train.py",
      "description": "Only allowed code-edit surface for benchmark experiments"
    },
    {
      "id": "E-PREPARE-01",
      "type": "EvaluationHarness",
      "file_path": "prepare.py",
      "ci_cd": "local-benchmark",
      "endpoint": "uv run prepare.py",
      "description": "Read-only benchmark harness defining constants, dataloading, tokenizer, and evaluation"
    },
    {
      "id": "E-PROGRAM-01",
      "type": "InstructionSpec",
      "file_path": "program.md",
      "ci_cd": "local-benchmark",
      "endpoint": "agent instruction context",
      "description": "Benchmark loop instructions and experiment policy"
    },
    {
      "id": "E-RESULTS-01",
      "type": "ExperimentLog",
      "file_path": "results.tsv",
      "ci_cd": "local-benchmark",
      "endpoint": "local artifact",
      "description": "Logging surface only; not part of executable benchmark logic"
    },
    {
      "id": "E-RUNLOG-01",
      "type": "RunOutput",
      "file_path": "run.log",
      "ci_cd": "local-benchmark",
      "endpoint": "local artifact",
      "description": "Captured training output used to extract benchmark metrics"
    }
  ]
}
<!-- ENTITY_REGISTRY_END -->
```
