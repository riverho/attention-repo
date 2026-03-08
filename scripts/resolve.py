"""Canonical path resolver for attention-layer skill.

Reads attention-config.json and resolves project paths without disk-wide search.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def load_config(skill_root: Path | None = None) -> dict[str, Any]:
    """Load attention-config.json from skill root."""
    if skill_root is None:
        # This file is in scripts/, skill root is parent
        skill_root = Path(__file__).parent.parent
    config_path = skill_root / "attention-config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing attention-config.json at {skill_root}")
    return json.loads(config_path.read_text(encoding="utf-8"))


def resolve_project_path(project_name: str, config: dict[str, Any] | None = None) -> Path:
    """Resolve canonical path for a registered project.

    Resolution order (configurable):
    1. Check canonical_path exists
    2. Search workspace_projects_root
    3. Git clone if source_strategy allows

    Raises:
        ValueError: If project not in registry
        FileNotFoundError: If path doesn't exist and clone fails
        RuntimeError: If disk-wide search is attempted (forbidden by config)
    """
    if config is None:
        config = load_config()

    registry = config.get("project_registry", {})
    if project_name not in registry:
        raise ValueError(
            f"Project '{project_name}' not in attention-config.json registry. "
            f"Known projects: {list(registry.keys())}"
        )

    project = registry[project_name]
    canonical = Path(project["canonical_path"])

    # 1. Check if canonical path exists
    if canonical.exists():
        return canonical.resolve()

    # 2. Check workspace projects root
    resolution = config.get("path_resolution", {})
    workspace_root = resolution.get("workspace_projects_root")
    if workspace_root:
        alt_path = Path(workspace_root) / project_name
        if alt_path.exists():
            return alt_path.resolve()

    # 3. Git clone if allowed
    strategy = project.get("source_strategy", "fail")
    git_remote = project.get("git_remote")

    if strategy == "git_clone_if_missing" and git_remote:
        canonical.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                ["git", "clone", git_remote, str(canonical)],
                check=True,
                capture_output=True,
                text=True,
            )
            return canonical.resolve()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to clone {git_remote}: {e.stderr}") from e

    # Forbidden fallbacks
    if config.get("validation", {}).get("forbid_disk_wide_search", False):
        raise RuntimeError(
            f"Project '{project_name}' not found at canonical path: {canonical}\n"
            f"Disk-wide search is FORBIDDEN by attention-config.json.\n"
            f"Options:\n"
            f"  1. Clone manually: git clone {git_remote or '<no remote>'} {canonical}\n"
            f"  2. Update canonical_path in attention-config.json\n"
            f"  3. Change source_strategy to 'git_clone_if_missing'"
        )

    raise FileNotFoundError(f"Could not resolve project: {project_name}")


def get_entity_resolution_path(project_name: str, artifact: str, config: dict[str, Any] | None = None) -> Path:
    """Get path to specific artifact (e.g., !MAP.md) for a project."""
    if config is None:
        config = load_config()

    registry = config.get("project_registry", {})
    if project_name not in registry:
        raise ValueError(f"Project '{project_name}' not in registry")

    project = registry[project_name]
    resolution = project.get("entity_resolution", {})

    if artifact not in resolution:
        # Default: artifact at canonical path root
        return resolve_project_path(project_name, config) / artifact

    template = resolution[artifact]
    canonical = Path(project["canonical_path"])
    path_str = template.replace("${canonical_path}", str(canonical))
    return Path(path_str).resolve()


def list_registered_projects(config: dict[str, Any] | None = None) -> list[str]:
    """Return list of registered project names."""
    if config is None:
        config = load_config()
    return list(config.get("project_registry", {}).keys())


def get_model_for_task(task: str, config: dict[str, Any] | None = None) -> str:
    """Get model alias for a specific task type."""
    if config is None:
        config = load_config()
    model_config = config.get("model_usage", {})
    task_models = model_config.get("tasks", {})
    return task_models.get(task, model_config.get("default", "minimax-portal/MiniMax-M2.5"))
