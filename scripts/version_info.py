#!/usr/bin/env python3
"""Canonical version loader for attention-repo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = SKILL_ROOT / "version.json"


def load_version_info() -> dict[str, Any]:
    try:
        payload = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Missing canonical version file: {VERSION_FILE}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid canonical version file: {VERSION_FILE}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError(f"Version file must contain a JSON object: {VERSION_FILE}")
    return payload


def get_version() -> str:
    payload = load_version_info()
    version = payload.get("version")
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError(f"Version file is missing a non-empty 'version' field: {VERSION_FILE}")
    return version.strip()


def main() -> None:
    print(get_version())


if __name__ == "__main__":
    main()
