#!/usr/bin/env python3
"""
Summarize raw benchmark results into summary.json for an Attention Repo case.

Usage:
    python3 scripts/summarize_case_results.py docs/cases/autoresearch-intent-gate
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_dir", help="Path to case directory")
    return parser.parse_args()


def load_summary(path: Path) -> dict:
    return json.loads(path.read_text())


def load_rows(path: Path) -> list[dict]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def to_float(value: str | None) -> float | None:
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def to_flag(value: str | None) -> bool:
    return str(value).strip() == "1"


def average_rate(rows: list[dict], key: str) -> float | None:
    if not rows:
        return None
    return sum(1 for row in rows if to_flag(row.get(key))) / len(rows)


def compute_best_val_bpb(rows: list[dict]) -> float | None:
    best = None
    for row in rows:
        if not to_flag(row.get("success")):
            continue
        if to_flag(row.get("reverted")):
            continue
        metric = to_float(row.get("primary_metric"))
        if metric is None or metric <= 0:
            continue
        best = metric if best is None else min(best, metric)
    return best


def compute_retained_improvement_rate(rows: list[dict]) -> float | None:
    if not rows:
        return None
    retained_improvements = 0
    baseline = None
    considered = 0
    for row in rows:
        metric = to_float(row.get("primary_metric"))
        success = to_flag(row.get("success"))
        reverted = to_flag(row.get("reverted"))
        if not success or metric is None or metric <= 0:
            considered += 1
            continue
        considered += 1
        if reverted:
            continue
        if baseline is None or metric < baseline:
            retained_improvements += 1
            baseline = metric
    return retained_improvements / considered if considered else None


def compute_wasted_runs_before_first_retained_improvement(rows: list[dict]) -> int | None:
    if not rows:
        return None
    baseline = None
    wasted = 0
    for row in rows:
        metric = to_float(row.get("primary_metric"))
        success = to_flag(row.get("success"))
        reverted = to_flag(row.get("reverted"))
        if not success or metric is None or metric <= 0 or reverted:
            wasted += 1
            continue
        if baseline is None or metric < baseline:
            return wasted
        wasted += 1
    return None


def round_or_none(value: float | None, digits: int = 4):
    if value is None:
        return None
    return round(value, digits)


def set_condition_summary(summary: dict, name: str, rows: list[dict]) -> None:
    summary[name] = {
        "retained_improvement_rate": round_or_none(compute_retained_improvement_rate(rows), 4),
        "invalid_edit_rate": round_or_none(average_rate(rows, "invalid_edit"), 4),
        "crash_rate": round_or_none(average_rate(rows, "crash"), 4),
        "wasted_runs_before_first_retained_improvement": compute_wasted_runs_before_first_retained_improvement(rows),
        "revert_rate": round_or_none(average_rate(rows, "reverted"), 4),
        "best_achieved_val_bpb": round_or_none(compute_best_val_bpb(rows), 6),
    }


def compute_delta(control: dict, treatment: dict) -> dict:
    keys = [
        "retained_improvement_rate",
        "invalid_edit_rate",
        "crash_rate",
        "wasted_runs_before_first_retained_improvement",
        "revert_rate",
        "best_achieved_val_bpb",
    ]
    delta = {}
    for key in keys:
        c = control.get(key)
        t = treatment.get(key)
        if c is None or t is None:
            delta[key] = None
        else:
            delta[key] = round(t - c, 6)
    return delta


def build_findings(control: dict, treatment: dict) -> list[str]:
    findings = []

    pairs = [
        ("retained improvement rate", "retained_improvement_rate", True),
        ("invalid edit rate", "invalid_edit_rate", False),
        ("crash rate", "crash_rate", False),
        ("revert rate", "revert_rate", False),
    ]
    for label, key, higher_is_better in pairs:
        c = control.get(key)
        t = treatment.get(key)
        if c is None or t is None:
            continue
        if higher_is_better and t > c:
            findings.append(f"Treatment improved {label} from {c:.2%} to {t:.2%}.")
        elif not higher_is_better and t < c:
            findings.append(f"Treatment reduced {label} from {c:.2%} to {t:.2%}.")

    c_best = control.get("best_achieved_val_bpb")
    t_best = treatment.get("best_achieved_val_bpb")
    if c_best is not None and t_best is not None and t_best < c_best:
        findings.append(f"Treatment reached a lower best retained val_bpb ({t_best:.6f} vs {c_best:.6f}).")

    return findings[:3]


def main() -> None:
    args = parse_args()
    case_dir = Path(args.case_dir).resolve()
    summary_path = case_dir / "summary.json"
    raw_path = case_dir / "raw-results.tsv"

    summary = load_summary(summary_path)
    rows = load_rows(raw_path)

    control_rows = [row for row in rows if row.get("condition", "").strip().lower() == "control"]
    treatment_rows = [row for row in rows if row.get("condition", "").strip().lower() == "treatment"]

    summary["run_count"] = len(rows)
    set_condition_summary(summary, "control", control_rows)
    set_condition_summary(summary, "treatment", treatment_rows)
    summary["delta"] = compute_delta(summary["control"], summary["treatment"])
    summary["key_findings"] = build_findings(summary["control"], summary["treatment"])

    summary_path.write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
