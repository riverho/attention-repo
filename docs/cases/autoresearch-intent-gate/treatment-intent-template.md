# Treatment Intent Template

Use this declare-intent shape before each treatment run.

## Required Fields

- Entities: `E-TRAIN-01`
- Pipeline: `local-benchmark`
- Requires New Entity: `False`

## First Principle Summary Template

`Try <short hypothesis> in train.py to improve val_bpb without changing prepare.py or the benchmark harness.`

## Example

- Entities: `E-TRAIN-01`
- Pipeline: `local-benchmark`
- First Principle: `Try a narrower optimizer change in train.py to improve val_bpb without changing prepare.py or the benchmark harness.`
- Requires New Entity: `False`
