#!/usr/bin/env python3
"""Shared helpers for global attention-state persistence."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_ROOT_ENV = "ATTENTION_REPO_STATE_ROOT"
OPENCLAW_CONFIG_ENV = "OPENCLAW_CONFIG_PATH"
DEFAULT_OPENCLAW_ROOT = Path.home() / ".openclaw"
DEFAULT_WORKSPACE_DIR = DEFAULT_OPENCLAW_ROOT / "workspace"
STATE_FILE_NAME = ".attention-state.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expand_path(raw: str | Path) -> Path:
    return Path(raw).expanduser()


def _load_openclaw_workspace_dir() -> Path:
    override = os.environ.get(OPENCLAW_CONFIG_ENV)
    config_path = _expand_path(override) if override else DEFAULT_OPENCLAW_ROOT / "openclaw.json"
    if not config_path.exists():
        return DEFAULT_WORKSPACE_DIR
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return DEFAULT_WORKSPACE_DIR
    workspace = config.get("agents", {}).get("defaults", {}).get("workspace")
    if isinstance(workspace, str) and workspace.strip():
        return _expand_path(workspace)
    return DEFAULT_WORKSPACE_DIR


def get_state_file() -> Path:
    override = os.environ.get(STATE_ROOT_ENV)
    if override:
        return _expand_path(override) / STATE_FILE_NAME
    return _load_openclaw_workspace_dir() / STATE_FILE_NAME


def get_state() -> dict[str, Any]:
    """Load global attention state."""
    state_file = get_state_file()
    if not state_file.exists():
        return {"active": None, "attended_repos": {}}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"active": None, "attended_repos": {}}


def save_state(state: dict[str, Any]) -> None:
    """Save global attention state."""
    state_file = get_state_file()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def set_active(repo_path: str, repo_name: str | None = None) -> dict[str, Any]:
    """Set active attention to a repo."""
    state = get_state()
    now = _utc_now()
    resolved_name = repo_name or Path(repo_path).name

    state["active"] = resolved_name
    state["active_path"] = str(repo_path)
    state["attended_at"] = now
    state.pop("released_at", None)
    state.pop("release_note", None)

    attended_repos = state.setdefault("attended_repos", {})
    attended_repos[resolved_name] = {
        "path": str(repo_path),
        "last_attended": now,
    }

    save_state(state)
    return state


def release_active(note: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Release active attention."""
    state = get_state()
    released = {
        "name": state.get("active"),
        "path": state.get("active_path"),
    }

    state["active"] = None
    state["active_path"] = None
    state["released_at"] = _utc_now()
    if note:
        state["release_note"] = note
    else:
        state.pop("release_note", None)

    save_state(state)
    return released, state


def get_active() -> dict[str, Any] | None:
    """Get currently active repo info."""
    state = get_state()
    if not state.get("active"):
        return None
    return {
        "name": state["active"],
        "path": state.get("active_path"),
        "attended_at": state.get("attended_at"),
    }


def list_attended() -> dict[str, Any]:
    """List all attended repos."""
    return get_state().get("attended_repos", {})
