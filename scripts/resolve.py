"""Central config, project discovery, and index helpers for attention_layer."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).parent.parent
LEGACY_CONFIG_PATH = SKILL_ROOT / "attention-config.json"
LEGACY_INDEX_PATH = SKILL_ROOT / ".attention" / "index.json"
DEFAULT_OPENCLAW_ROOT = Path.home() / ".openclaw"
DEFAULT_WORKSPACE_ROOT = DEFAULT_OPENCLAW_ROOT / "workspace"
OPENCLAW_CONFIG_ENV = "OPENCLAW_CONFIG_PATH"
STATE_ROOT_ENV = "ATTENTION_LAYER_STATE_ROOT"
CONFIG_PATH_ENV = "ATTENTION_LAYER_CONFIG_PATH"
INDEX_PATH_ENV = "ATTENTION_LAYER_INDEX_PATH"
CANDIDATE_MARKERS = [".git", "package.json", "pyproject.toml", "Cargo.toml", "go.mod", "README.md"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expand_path(raw: str | Path) -> Path:
    return Path(raw).expanduser()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_openclaw_config_path() -> Path:
    override = os.environ.get(OPENCLAW_CONFIG_ENV)
    if override:
        return _expand_path(override)
    return DEFAULT_OPENCLAW_ROOT / "openclaw.json"


def load_openclaw_config() -> dict[str, Any]:
    path = get_openclaw_config_path()
    if not path.exists():
        raise FileNotFoundError(f"Missing OpenClaw config: {path}")
    return _read_json(path)


def get_state_root() -> Path:
    override = os.environ.get(STATE_ROOT_ENV)
    if override:
        return _expand_path(override)
    return DEFAULT_OPENCLAW_ROOT / "attention-layer"


def get_config_path() -> Path:
    override = os.environ.get(CONFIG_PATH_ENV)
    if override:
        return _expand_path(override)
    return get_state_root() / "config.json"


def get_index_path() -> Path:
    override = os.environ.get(INDEX_PATH_ENV)
    if override:
        return _expand_path(override)
    return get_state_root() / "index.json"


def central_config_exists() -> bool:
    return get_config_path().exists()


def _extract_openclaw_workspace_root(openclaw_cfg: dict[str, Any]) -> Path:
    workspace = (
        openclaw_cfg.get("agents", {})
        .get("defaults", {})
        .get("workspace")
    )
    if isinstance(workspace, str) and workspace.strip():
        return _expand_path(workspace)
    return DEFAULT_WORKSPACE_ROOT


def _extract_openclaw_default_model(openclaw_cfg: dict[str, Any]) -> str:
    primary = (
        openclaw_cfg.get("agents", {})
        .get("defaults", {})
        .get("model", {})
        .get("primary")
    )
    if isinstance(primary, str) and primary.strip():
        return primary.strip()
    return "auto"


def _extract_openclaw_fallback_models(openclaw_cfg: dict[str, Any]) -> list[str]:
    fallbacks = (
        openclaw_cfg.get("agents", {})
        .get("defaults", {})
        .get("model", {})
        .get("fallbacks", [])
    )
    if not isinstance(fallbacks, list):
        return []
    return [str(item).strip() for item in fallbacks if str(item).strip()]


def _extract_available_models(openclaw_cfg: dict[str, Any]) -> list[str]:
    available: list[str] = []
    defaults_models = openclaw_cfg.get("agents", {}).get("defaults", {}).get("models", {})
    if isinstance(defaults_models, dict):
        available.extend(str(key).strip() for key in defaults_models if str(key).strip())

    providers = openclaw_cfg.get("models", {}).get("providers", {})
    if isinstance(providers, dict):
        for provider_name, provider_data in providers.items():
            models = provider_data.get("models", []) if isinstance(provider_data, dict) else []
            if not isinstance(models, list):
                continue
            for model in models:
                if not isinstance(model, dict):
                    continue
                model_id = str(model.get("id", "")).strip()
                if model_id:
                    available.append(f"{provider_name}/{model_id}")
    return sorted({item for item in available if item})


def build_default_config(openclaw_cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    if openclaw_cfg is None:
        openclaw_cfg = load_openclaw_config()

    workspace_root = _extract_openclaw_workspace_root(openclaw_cfg)
    default_model = _extract_openclaw_default_model(openclaw_cfg)
    fallback_models = _extract_openclaw_fallback_models(openclaw_cfg)
    available_models = _extract_available_models(openclaw_cfg)
    state_root = get_state_root()

    return {
        "$schema": "attention-layer-config-v2",
        "openclaw": {
            "config_path": str(get_openclaw_config_path()),
            "inherit_workspace_root": True,
            "inherit_default_model": True,
            "inherit_available_models": True,
        },
        "paths": {
            "state_root": str(state_root),
            "default_scan_roots": [str(workspace_root / "projects")],
            "optional_scan_roots": {
                "skills": str(workspace_root / "skills"),
                "plugins": str(DEFAULT_OPENCLAW_ROOT / "plugins"),
            },
        },
        "discovery": {
            "mode": "projects_only",
            "max_depth": 1,
            "candidate_markers": list(CANDIDATE_MARKERS),
            "include_skills_only_when_requested": True,
            "include_plugins_only_when_requested": True,
        },
        "models": {
            "default": "auto",
            "fallbacks": "openclaw",
            "available": available_models,
            "tasks": {
                "architectural_analysis": "auto",
                "code_generation": "auto",
                "documentation": "auto",
            },
            "resolved": {
                "openclaw_default": default_model,
                "openclaw_fallbacks": fallback_models,
            },
        },
        "projects": {},
    }


def _normalize_legacy_config(config: dict[str, Any], openclaw_cfg: dict[str, Any]) -> dict[str, Any]:
    normalized = build_default_config(openclaw_cfg)
    registry = config.get("project_registry", {})
    if isinstance(registry, dict):
        normalized["projects"] = registry

    path_resolution = config.get("path_resolution", {})
    if isinstance(path_resolution, dict):
        workspace_root = path_resolution.get("workspace_projects_root")
        if isinstance(workspace_root, str) and workspace_root.strip():
            normalized["paths"]["default_scan_roots"] = [workspace_root.strip()]

    model_usage = config.get("model_usage", {})
    if isinstance(model_usage, dict):
        normalized["models"]["default"] = model_usage.get("default", normalized["models"]["default"])
        normalized["models"]["tasks"] = model_usage.get("tasks", normalized["models"]["tasks"])

    validation = config.get("validation", {})
    if isinstance(validation, dict):
        normalized["validation"] = validation
    return normalized


def load_config(skill_root: Path | None = None) -> dict[str, Any]:
    del skill_root  # Legacy callers still pass this.
    openclaw_cfg = load_openclaw_config()
    central_path = get_config_path()
    if central_path.exists():
        config = _read_json(central_path)
        if "projects" not in config and "project_registry" in config:
            return _normalize_legacy_config(config, openclaw_cfg)
        return config
    if LEGACY_CONFIG_PATH.exists():
        return _normalize_legacy_config(_read_json(LEGACY_CONFIG_PATH), openclaw_cfg)
    raise FileNotFoundError(
        "Missing attention-layer config. Run `scripts/attention init-config` to create "
        f"{central_path}."
    )


def save_config(config: dict[str, Any], path: Path | None = None) -> Path:
    out = path or get_config_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return out


def get_project_registry(config: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    if config is None:
        config = load_config()
    registry = config.get("projects")
    if isinstance(registry, dict):
        return registry
    legacy = config.get("project_registry")
    if isinstance(legacy, dict):
        return legacy
    return {}


def list_registered_projects(config: dict[str, Any] | None = None) -> list[str]:
    return sorted(get_project_registry(config).keys())


def resolve_project_path(project_name: str, config: dict[str, Any] | None = None) -> Path:
    if config is None:
        config = load_config()

    registry = get_project_registry(config)
    if project_name not in registry:
        raise ValueError(
            f"Project '{project_name}' not in config registry. Known projects: {list(registry.keys())}"
        )

    project = registry[project_name]
    canonical = _expand_path(project["canonical_path"])
    if canonical.exists():
        return canonical.resolve()

    scan_roots = config.get("paths", {}).get("default_scan_roots", [])
    for root in scan_roots:
        alt_path = _expand_path(root) / project_name
        if alt_path.exists():
            return alt_path.resolve()

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
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"Failed to clone {git_remote}: {exc.stderr}") from exc

    raise FileNotFoundError(f"Could not resolve project '{project_name}' at {canonical}")


def get_entity_resolution_path(project_name: str, artifact: str, config: dict[str, Any] | None = None) -> Path:
    if config is None:
        config = load_config()

    registry = get_project_registry(config)
    if project_name not in registry:
        raise ValueError(f"Project '{project_name}' not in registry")

    project = registry[project_name]
    resolution = project.get("entity_resolution", {})
    if artifact not in resolution:
        return resolve_project_path(project_name, config) / artifact

    template = str(resolution[artifact])
    canonical = _expand_path(project["canonical_path"])
    return Path(template.replace("${canonical_path}", str(canonical))).expanduser()


def get_model_for_task(task: str, config: dict[str, Any] | None = None) -> str:
    if config is None:
        config = load_config()
    model_config = config.get("models", {})
    task_models = model_config.get("tasks", {})
    selected = task_models.get(task, model_config.get("default", "auto"))
    if selected != "auto":
        return str(selected)
    resolved = model_config.get("resolved", {})
    return str(resolved.get("openclaw_default", "auto"))


def get_available_models(config: dict[str, Any] | None = None) -> list[str]:
    if config is None:
        config = load_config()
    models = config.get("models", {}).get("available", [])
    if isinstance(models, list):
        return [str(item).strip() for item in models if str(item).strip()]
    return []


def default_index_payload() -> dict[str, Any]:
    now = utc_now()
    return {
        "version": "1",
        "created_at": now,
        "last_updated": now,
        "projects": {},
    }


def ensure_index(index_path: Path | None = None) -> Path:
    path = index_path or get_index_path()
    if path.exists():
        return path
    legacy_path = LEGACY_INDEX_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if legacy_path.exists():
        path.write_text(legacy_path.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        path.write_text(json.dumps(default_index_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def load_index(index_path: Path | None = None) -> dict[str, Any]:
    path = ensure_index(index_path)
    try:
        return _read_json(path)
    except json.JSONDecodeError:
        payload = default_index_payload()
        save_index(payload, path)
        return payload


def save_index(index: dict[str, Any], index_path: Path | None = None) -> Path:
    path = index_path or get_index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    index["last_updated"] = utc_now()
    path.write_text(json.dumps(index, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def resolve_project_name_from_path(repo: Path, config: dict[str, Any] | None = None) -> str | None:
    if config is None:
        config = load_config()
    repo_resolved = repo.resolve()
    for name, entry in get_project_registry(config).items():
        canonical = _expand_path(entry.get("canonical_path", ""))
        try:
            if canonical.exists() and canonical.resolve() == repo_resolved:
                return name
        except OSError:
            continue
        if canonical == repo_resolved:
            return name
    return None


def summarize_current_task(repo: Path) -> tuple[str, str]:
    task_path = repo / "CURRENT_TASK.md"
    if not task_path.exists():
        return "missing", ""
    text = task_path.read_text(encoding="utf-8", errors="replace")
    lowered = text.lower()
    status = "idle"
    if "completed" in lowered:
        status = "completed"
    elif "in progress" in lowered or "active" in lowered:
        status = "active"

    summary = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("<!--"):
            continue
        summary = line
        break
    return status, summary[:240]


def _days_since(timestamp: str) -> float:
    then = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return (now - then).total_seconds() / 86400


def refresh_project_record(
    project_name: str,
    canonical_path: str | Path,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _expand_path(canonical_path)
    record = dict(existing or {})
    record["canonical_path"] = str(repo)
    record["exists"] = repo.exists()
    record["has_map"] = (repo / "!MAP.md").exists()
    record["has_task"] = (repo / "CURRENT_TASK.md").exists()
    task_status, task_summary = summarize_current_task(repo)
    record["status"] = task_status
    record["task_summary"] = task_summary
    warnings: list[str] = []
    stale = False

    last_assemble = record.get("last_assemble")
    if isinstance(last_assemble, str) and last_assemble:
        if _days_since(last_assemble) > 7:
            stale = True
            warnings.append("Not assembled in 7+ days")
        map_path = repo / "!MAP.md"
        if map_path.exists():
            map_mtime = datetime.fromtimestamp(map_path.stat().st_mtime, tz=timezone.utc)
            assemble_time = datetime.fromisoformat(last_assemble.replace("Z", "+00:00"))
            if map_mtime > assemble_time:
                stale = True
                warnings.append("!MAP.md modified since last assemble")

    last_freshness = record.get("last_freshness")
    if isinstance(last_freshness, str) and last_freshness and _days_since(last_freshness) > 7:
        stale = True
        warnings.append("Freshness not checked in 7+ days")

    record["stale"] = stale
    record["warnings"] = warnings
    return record


def record_project_operation(
    project_name: str,
    canonical_path: str | Path,
    operation: str,
    result: str = "ok",
    extra: dict[str, Any] | None = None,
    index_path: Path | None = None,
) -> Path:
    index = load_index(index_path)
    projects = index.setdefault("projects", {})
    existing = projects.get(project_name, {})
    record = refresh_project_record(project_name, canonical_path, existing)
    record["last_operation"] = operation
    record["last_result"] = result
    record["last_event_at"] = utc_now()

    field_map = {
        "declare-intent": "last_declare_intent",
        "assemble": "last_assemble",
        "freshness": "last_freshness",
        "finalize-change": "last_finalize",
        "sync-state": "last_sync_state",
        "update-task": "last_update_task",
        "clear-task": "last_clear_task",
        "repair": "last_repair",
        "reindex": "last_reindex",
        "init": "last_init",
    }
    if operation in field_map:
        record[field_map[operation]] = record["last_event_at"]

    if extra:
        record.update(extra)

    projects[project_name] = record
    return save_index(index, index_path)


def reindex_registered_projects(config: dict[str, Any] | None = None, index_path: Path | None = None) -> Path:
    if config is None:
        config = load_config()
    index = load_index(index_path)
    projects = {}
    for name, entry in get_project_registry(config).items():
        projects[name] = refresh_project_record(name, entry["canonical_path"], index.get("projects", {}).get(name))
    index["projects"] = projects
    return save_index(index, index_path)


def register_project(
    config: dict[str, Any],
    project_name: str,
    canonical_path: str | Path,
    source: str = "discovered",
    managed: bool = True,
) -> None:
    registry = get_project_registry(config)
    registry[project_name] = {
        "canonical_path": str(_expand_path(canonical_path)),
        "source_strategy": "local_only",
        "managed": managed,
        "source": source,
    }
    config["projects"] = registry


def _classify_project_dir(project_dir: Path) -> tuple[bool, list[str]]:
    markers = []
    for marker in CANDIDATE_MARKERS:
        if (project_dir / marker).exists():
            markers.append(marker)
    return bool(markers), markers


def detect_project_candidates(
    config: dict[str, Any] | None = None,
    *,
    include_skills: bool = False,
    include_plugins: bool = False,
) -> list[dict[str, Any]]:
    if config is None:
        config = load_config()

    roots: list[tuple[str, Path]] = []
    for root in config.get("paths", {}).get("default_scan_roots", []):
        roots.append(("projects", _expand_path(root)))

    optional_roots = config.get("paths", {}).get("optional_scan_roots", {})
    if include_skills and optional_roots.get("skills"):
        roots.append(("skills", _expand_path(optional_roots["skills"])))
    if include_plugins and optional_roots.get("plugins"):
        roots.append(("plugins", _expand_path(optional_roots["plugins"])))

    registry = get_project_registry(config)
    candidates: list[dict[str, Any]] = []
    for scope, root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for child in sorted(root.iterdir(), key=lambda item: item.name.lower()):
            if child.name.startswith(".") or not child.is_dir():
                continue
            is_candidate, markers = _classify_project_dir(child)
            if not is_candidate:
                continue
            has_map = (child / "!MAP.md").exists()
            has_task = (child / "CURRENT_TASK.md").exists()
            if has_map and has_task:
                classification = "ready"
            elif has_map or has_task:
                classification = "partial"
            else:
                classification = "uninitialized"
            candidates.append(
                {
                    "name": child.name,
                    "canonical_path": str(child.resolve()),
                    "scope": scope,
                    "markers": markers,
                    "has_map": has_map,
                    "has_task": has_task,
                    "classification": classification,
                    "registered": child.name in registry,
                }
            )
    return candidates
