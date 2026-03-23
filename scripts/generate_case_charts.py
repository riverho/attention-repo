#!/usr/bin/env python3
"""
Generate simple SVG charts for an Attention Repo benchmark case.

Usage:
    python3 scripts/generate_case_charts.py docs/cases/autoresearch-intent-gate
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from html import escape
from pathlib import Path


WIDTH = 980
HEIGHT = 560
PLOT_LEFT = 110
PLOT_RIGHT = 60
PLOT_TOP = 90
PLOT_BOTTOM = 95
PLOT_WIDTH = WIDTH - PLOT_LEFT - PLOT_RIGHT
PLOT_HEIGHT = HEIGHT - PLOT_TOP - PLOT_BOTTOM

CONTROL_COLOR = "#A6B1C4"
TREATMENT_COLOR = "#1D4ED8"
GRID_COLOR = "#D7DEE8"
TEXT_COLOR = "#172033"
SUBTLE_TEXT = "#5B677A"
AXIS_COLOR = "#8A94A6"
NO_DATA_FILL = "#EEF2F7"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_dir", help="Path to case directory")
    return parser.parse_args()


def load_summary(case_dir: Path) -> dict:
    return json.loads((case_dir / "summary.json").read_text())


def load_rows(case_dir: Path) -> list[dict]:
    path = case_dir / "raw-results.tsv"
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def metric_direction(metric_name: str) -> str:
    name = metric_name.lower()
    if "loss" in name or "bpb" in name or "error" in name:
        return "lower"
    return "higher"


def to_float(value) -> float | None:
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def fmt_value(value: float | None, as_percent: bool = False) -> str:
    if value is None:
        return "n/a"
    if as_percent:
        return f"{value * 100:.1f}%"
    if abs(value) >= 100:
        return f"{value:.0f}"
    if abs(value) >= 10:
        return f"{value:.1f}"
    return f"{value:.3f}"


def chart_shell(title: str, subtitle: str, body: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
  <rect width="{WIDTH}" height="{HEIGHT}" fill="white"/>
  <text x="{PLOT_LEFT}" y="46" font-family="Helvetica, Arial, sans-serif" font-size="28" font-weight="700" fill="{TEXT_COLOR}">{escape(title)}</text>
  <text x="{PLOT_LEFT}" y="72" font-family="Helvetica, Arial, sans-serif" font-size="15" fill="{SUBTLE_TEXT}">{escape(subtitle)}</text>
  {body}
</svg>
"""


def no_data_body(message: str) -> str:
    return f"""
  <rect x="{PLOT_LEFT}" y="{PLOT_TOP}" width="{PLOT_WIDTH}" height="{PLOT_HEIGHT}" rx="16" fill="{NO_DATA_FILL}"/>
  <text x="{PLOT_LEFT + PLOT_WIDTH / 2:.1f}" y="{PLOT_TOP + PLOT_HEIGHT / 2 - 8:.1f}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="22" font-weight="600" fill="{TEXT_COLOR}">No chart data yet</text>
  <text x="{PLOT_LEFT + PLOT_WIDTH / 2:.1f}" y="{PLOT_TOP + PLOT_HEIGHT / 2 + 22:.1f}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="15" fill="{SUBTLE_TEXT}">{escape(message)}</text>
"""


def pick_bar_metric(summary: dict) -> tuple[str, float | None, float | None, bool]:
    control = summary.get("control", {})
    treatment = summary.get("treatment", {})
    candidates = [
        ("retained_improvement_rate", True),
        ("best_achieved_val_bpb", False),
        ("invalid_edit_rate", True),
        ("crash_rate", True),
    ]
    for key, as_percent in candidates:
        if key in control or key in treatment:
            return key, to_float(control.get(key)), to_float(treatment.get(key)), as_percent
    return "primary_metric", None, None, False


def render_bar_chart(title: str, subtitle: str, metric_label: str, control_value: float | None,
                     treatment_value: float | None, as_percent: bool, out_path: Path) -> None:
    if control_value is None and treatment_value is None:
        out_path.write_text(chart_shell(title, subtitle, no_data_body("Populate summary.json to generate this chart.")))
        return

    values = [v for v in [control_value, treatment_value] if v is not None]
    max_value = max(values) if values else 1.0
    top_value = max_value * 1.15 if max_value > 0 else 1.0
    if top_value == 0:
        top_value = 1.0

    grid = []
    for i in range(5):
        fraction = i / 4
        y = PLOT_TOP + PLOT_HEIGHT - (fraction * PLOT_HEIGHT)
        tick_value = top_value * fraction
        grid.append(
            f'<line x1="{PLOT_LEFT}" y1="{y:.1f}" x2="{PLOT_LEFT + PLOT_WIDTH}" y2="{y:.1f}" stroke="{GRID_COLOR}" stroke-width="1"/>'
        )
        grid.append(
            f'<text x="{PLOT_LEFT - 14}" y="{y + 5:.1f}" text-anchor="end" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="{SUBTLE_TEXT}">{escape(fmt_value(tick_value, as_percent))}</text>'
        )

    bar_width = 180
    gap = 140
    start_x = PLOT_LEFT + (PLOT_WIDTH - (2 * bar_width + gap)) / 2
    bars = []
    labels = [("Control", control_value, CONTROL_COLOR), ("Treatment", treatment_value, TREATMENT_COLOR)]
    for idx, (name, value, color) in enumerate(labels):
        x = start_x + idx * (bar_width + gap)
        height = 0 if value is None else (value / top_value) * PLOT_HEIGHT
        y = PLOT_TOP + PLOT_HEIGHT - height
        if value is None:
            bars.append(f'<rect x="{x:.1f}" y="{PLOT_TOP + PLOT_HEIGHT - 4:.1f}" width="{bar_width}" height="4" rx="2" fill="{color}" opacity="0.35"/>')
            bars.append(f'<text x="{x + bar_width / 2:.1f}" y="{PLOT_TOP + PLOT_HEIGHT / 2:.1f}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="14" fill="{SUBTLE_TEXT}">n/a</text>')
        else:
            bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width}" height="{height:.1f}" rx="10" fill="{color}"/>')
            bars.append(f'<text x="{x + bar_width / 2:.1f}" y="{y - 10:.1f}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="16" font-weight="600" fill="{TEXT_COLOR}">{escape(fmt_value(value, as_percent))}</text>')
        bars.append(f'<text x="{x + bar_width / 2:.1f}" y="{PLOT_TOP + PLOT_HEIGHT + 30:.1f}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="15" fill="{TEXT_COLOR}">{name}</text>')

    body = "\n".join(grid + bars + [
        f'<line x1="{PLOT_LEFT}" y1="{PLOT_TOP + PLOT_HEIGHT:.1f}" x2="{PLOT_LEFT + PLOT_WIDTH}" y2="{PLOT_TOP + PLOT_HEIGHT:.1f}" stroke="{AXIS_COLOR}" stroke-width="2"/>',
        f'<text x="{PLOT_LEFT + PLOT_WIDTH / 2:.1f}" y="{HEIGHT - 32}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="16" fill="{SUBTLE_TEXT}">{escape(metric_label)}</text>',
    ])
    out_path.write_text(chart_shell(title, subtitle, body))


def build_progression(rows: list[dict], direction: str) -> dict[str, list[tuple[int, float]]]:
    progress = {"control": [], "treatment": []}
    best = {"control": None, "treatment": None}
    counters = {"control": 0, "treatment": 0}

    for row in rows:
        condition = row.get("condition", "").strip().lower()
        if condition not in progress:
            continue
        counters[condition] += 1
        metric = to_float(row.get("primary_metric"))
        success = row.get("success") == "1"
        reverted = row.get("reverted") == "1"
        if metric is None or not success or reverted:
            current_best = best[condition]
        else:
            current_best = best[condition]
            if current_best is None:
                current_best = metric
            elif direction == "lower":
                current_best = min(current_best, metric)
            else:
                current_best = max(current_best, metric)
            best[condition] = current_best
        if current_best is not None:
            progress[condition].append((counters[condition], current_best))
    return progress


def render_line_chart(title: str, subtitle: str, metric_label: str, progress: dict[str, list[tuple[int, float]]],
                      out_path: Path) -> None:
    all_points = progress["control"] + progress["treatment"]
    if not all_points:
        out_path.write_text(chart_shell(title, subtitle, no_data_body("Populate raw-results.tsv to generate the progression chart.")))
        return

    xs = [point[0] for point in all_points]
    ys = [point[1] for point in all_points]
    min_y = min(ys)
    max_y = max(ys)
    if math.isclose(min_y, max_y):
        max_y = min_y + 1.0

    def x_map(x_value: float) -> float:
        span = max(xs) - min(xs) if max(xs) != min(xs) else 1
        return PLOT_LEFT + ((x_value - min(xs)) / span) * PLOT_WIDTH

    def y_map(y_value: float) -> float:
        return PLOT_TOP + PLOT_HEIGHT - ((y_value - min_y) / (max_y - min_y)) * PLOT_HEIGHT

    grid = []
    for i in range(5):
        fraction = i / 4
        y = PLOT_TOP + PLOT_HEIGHT - (fraction * PLOT_HEIGHT)
        tick_value = min_y + (max_y - min_y) * fraction
        grid.append(
            f'<line x1="{PLOT_LEFT}" y1="{y:.1f}" x2="{PLOT_LEFT + PLOT_WIDTH}" y2="{y:.1f}" stroke="{GRID_COLOR}" stroke-width="1"/>'
        )
        grid.append(
            f'<text x="{PLOT_LEFT - 14}" y="{y + 5:.1f}" text-anchor="end" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="{SUBTLE_TEXT}">{escape(fmt_value(tick_value))}</text>'
        )

    x_ticks = []
    max_x = max(xs)
    for i in range(1, max_x + 1):
        x = x_map(i)
        x_ticks.append(f'<line x1="{x:.1f}" y1="{PLOT_TOP + PLOT_HEIGHT}" x2="{x:.1f}" y2="{PLOT_TOP + PLOT_HEIGHT + 6}" stroke="{AXIS_COLOR}" stroke-width="1"/>')
        if i == 1 or i == max_x or i % max(1, max_x // 6) == 0:
            x_ticks.append(f'<text x="{x:.1f}" y="{PLOT_TOP + PLOT_HEIGHT + 28}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="{SUBTLE_TEXT}">{i}</text>')

    lines = []
    legend = []
    for idx, (name, color) in enumerate([("control", CONTROL_COLOR), ("treatment", TREATMENT_COLOR)]):
        points = progress[name]
        if not points:
            continue
        polyline = " ".join(f"{x_map(x):.1f},{y_map(y):.1f}" for x, y in points)
        lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" points="{polyline}"/>')
        for x_value, y_value in points:
            lines.append(f'<circle cx="{x_map(x_value):.1f}" cy="{y_map(y_value):.1f}" r="4.5" fill="{color}"/>')
        legend_x = PLOT_LEFT + idx * 150
        legend.append(f'<rect x="{legend_x}" y="{HEIGHT - 52}" width="18" height="18" rx="4" fill="{color}"/>')
        legend.append(f'<text x="{legend_x + 28}" y="{HEIGHT - 38}" font-family="Helvetica, Arial, sans-serif" font-size="15" fill="{TEXT_COLOR}">{name.title()}</text>')

    body = "\n".join(grid + x_ticks + lines + legend + [
        f'<line x1="{PLOT_LEFT}" y1="{PLOT_TOP + PLOT_HEIGHT:.1f}" x2="{PLOT_LEFT + PLOT_WIDTH}" y2="{PLOT_TOP + PLOT_HEIGHT:.1f}" stroke="{AXIS_COLOR}" stroke-width="2"/>',
        f'<line x1="{PLOT_LEFT}" y1="{PLOT_TOP}" x2="{PLOT_LEFT}" y2="{PLOT_TOP + PLOT_HEIGHT}" stroke="{AXIS_COLOR}" stroke-width="2"/>',
        f'<text x="{PLOT_LEFT + PLOT_WIDTH / 2:.1f}" y="{HEIGHT - 14}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="16" fill="{SUBTLE_TEXT}">Run index</text>',
        f'<text x="28" y="{PLOT_TOP + PLOT_HEIGHT / 2:.1f}" transform="rotate(-90 28 {PLOT_TOP + PLOT_HEIGHT / 2:.1f})" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="16" fill="{SUBTLE_TEXT}">{escape(metric_label)}</text>',
    ])
    out_path.write_text(chart_shell(title, subtitle, body))


def main() -> None:
    args = parse_args()
    case_dir = Path(args.case_dir).resolve()
    summary = load_summary(case_dir)
    rows = load_rows(case_dir)
    charts_dir = case_dir / "charts"
    ensure_dir(charts_dir)

    case_slug = summary.get("case_slug", case_dir.name)
    primary_metric_name = summary.get("primary_metric_name", "primary_metric")
    direction = metric_direction(primary_metric_name)

    metric_key, control_value, treatment_value, as_percent = pick_bar_metric(summary)
    render_bar_chart(
        title=f"{case_slug}: primary comparison",
        subtitle=f"Control vs treatment on {metric_key}",
        metric_label=metric_key,
        control_value=control_value,
        treatment_value=treatment_value,
        as_percent=as_percent,
        out_path=charts_dir / "before-after-bar.svg",
    )

    render_bar_chart(
        title=f"{case_slug}: error-rate comparison",
        subtitle="Control vs treatment on invalid edits",
        metric_label="invalid_edit_rate",
        control_value=to_float(summary.get("control", {}).get("invalid_edit_rate")),
        treatment_value=to_float(summary.get("treatment", {}).get("invalid_edit_rate")),
        as_percent=True,
        out_path=charts_dir / "error-rate-bar.svg",
    )

    render_line_chart(
        title=f"{case_slug}: best-so-far progression",
        subtitle=f"Best retained {primary_metric_name} by run index",
        metric_label=primary_metric_name,
        progress=build_progression(rows, direction),
        out_path=charts_dir / "progression-line.svg",
    )

    manifest = {
        "case_slug": case_slug,
        "charts": [
            "charts/before-after-bar.svg",
            "charts/error-rate-bar.svg",
            "charts/progression-line.svg",
        ],
    }
    (charts_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
