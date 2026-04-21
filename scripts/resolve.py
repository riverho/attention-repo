"""Central config, project discovery, and index helpers for attention_repo."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from version_info import get_version
except ModuleNotFoundError:
    from scripts.version_info import get_version


SKILL_ROOT = Path(__file__).parent.parent
ATTENTION_VERSION = get_version()
LEGACY_CONFIG_PATH = SKILL_ROOT / "attention-config.json"
LEGACY_INDEX_PATH = SKILL_ROOT / ".attention" / "index.json"
DEFAULT_OPENCLAW_ROOT = Path.home() / ".openclaw"
DEFAULT_WORKSPACE_ROOT = DEFAULT_OPENCLAW_ROOT / "workspace"
OPENCLAW_CONFIG_ENV = "OPENCLAW_CONFIG_PATH"
STATE_ROOT_ENV = "ATTENTION_REPO_STATE_ROOT"
CONFIG_PATH_ENV = "ATTENTION_REPO_CONFIG_PATH"
INDEX_PATH_ENV = "ATTENTION_REPO_INDEX_PATH"
CANDIDATE_MARKERS = [".git", "package.json", "pyproject.toml", "Cargo.toml", "go.mod", "README.md"]
RESERVED_PROJECT_TOKENS = {
    "attention",
    "attention-repo",
    "attention_repo",
    "init",
    "no",
    "n",
    "projects",
    "start",
    "wrap",
    "yes",
    "y",
}
SKILL_RUNTIME_KEY = "skill_runtime"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_skill_runtime_payload(*, timestamp: str | None = None) -> dict[str, Any]:
    compiled_at = timestamp or utc_now()
    return {
        "compiled_version": ATTENTION_VERSION,
        "compiled_at": compiled_at,
        "skill_path": str(SKILL_ROOT),
        "map_path": str(SKILL_ROOT / "!MAP.md"),
        "task_path": str(SKILL_ROOT / "CURRENT_TASK.md"),
        "map_valid": (SKILL_ROOT / "!MAP.md").exists(),
        "task_valid": (SKILL_ROOT / "CURRENT_TASK.md").exists(),
        "task_status": "",
        "task_summary": "",
    }


def _expand_path(raw: str | Path) -> Path:
    return Path(raw).expanduser()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_lookup_token(raw: str) -> str:
    token = re.sub(r"[\s_]+", "-", raw.strip().lower())
    token = re.sub(r"-{2,}", "-", token)
    return token.strip("-")


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
    return DEFAULT_OPENCLAW_ROOT / "attention-repo"


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
        "$schema": "attention-repo-config-v3",
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
            "menu_visible_scopes": ["projects", "skills"],
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


def _merge_legacy_projects_into_central(
    central_config: dict[str, Any],
    legacy_config: dict[str, Any],
    openclaw_cfg: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(central_config)
    merged_projects = dict(central_config.get("projects", {}))
    legacy_projects = _normalize_legacy_config(legacy_config, openclaw_cfg).get("projects", {})
    for name, entry in legacy_projects.items():
        if name not in merged_projects:
            merged_projects[name] = entry
    merged["projects"] = merged_projects
    return merged


def load_config(skill_root: Path | None = None) -> dict[str, Any]:
    del skill_root  # Legacy callers still pass this.
    openclaw_cfg = load_openclaw_config()
    central_path = get_config_path()
    if central_path.exists():
        config = _read_json(central_path)
        if "projects" not in config and "project_registry" in config:
            normalized = _normalize_legacy_config(config, openclaw_cfg)
            save_config(normalized, central_path)
            return normalized
        central_projects = config.get("projects", {})
        if (
            isinstance(central_projects, dict)
            and not central_projects
            and LEGACY_CONFIG_PATH.exists()
        ):
            merged = _merge_legacy_projects_into_central(
                config,
                _read_json(LEGACY_CONFIG_PATH),
                openclaw_cfg,
            )
            save_config(merged, central_path)
            return merged
        return config
    if LEGACY_CONFIG_PATH.exists():
        return _normalize_legacy_config(_read_json(LEGACY_CONFIG_PATH), openclaw_cfg)
    raise FileNotFoundError(
        "Missing attention-repo config. Run `scripts/attention init-config` to create "
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


def get_project_display_name(project_name: str, config: dict[str, Any] | None = None) -> str:
    registry = get_project_registry(config)
    entry = registry.get(project_name, {})
    display_name = str(entry.get("display_name", "")).strip()
    if display_name:
        return display_name
    canonical_raw = str(entry.get("canonical_path", "")).strip()
    if canonical_raw:
        basename = _expand_path(canonical_raw).name.strip()
        if basename and basename != project_name:
            return basename
    return project_name


def get_project_aliases(project_name: str, config: dict[str, Any] | None = None) -> list[str]:
    registry = get_project_registry(config)
    entry = registry.get(project_name, {})
    aliases: list[str] = []
    raw_aliases = entry.get("aliases", [])
    if isinstance(raw_aliases, list):
        aliases.extend(str(alias).strip() for alias in raw_aliases if str(alias).strip())

    display_name = str(entry.get("display_name", "")).strip()
    if display_name and display_name != project_name:
        aliases.append(display_name)

    canonical_raw = str(entry.get("canonical_path", "")).strip()
    if canonical_raw:
        basename = _expand_path(canonical_raw).name.strip()
        if basename and basename != project_name:
            aliases.append(basename)

    deduped: list[str] = []
    seen: set[str] = set()
    project_token = _normalize_lookup_token(project_name)
    for alias in aliases:
        token = _normalize_lookup_token(alias)
        if not token or token == project_token:
            continue
        if token in RESERVED_PROJECT_TOKENS:
            continue
        if token in seen:
            continue
        seen.add(token)
        deduped.append(alias)
    return deduped


def resolve_project_key(
    project_name: str,
    config: dict[str, Any] | None = None,
    *,
    allow_fuzzy: bool = True,
) -> str:
    if config is None:
        config = load_config()

    registry = get_project_registry(config)
    if not registry:
        raise ValueError("No registered projects.")

    exact = project_name.strip()
    if exact in registry:
        return exact

    normalized_input = _normalize_lookup_token(project_name)
    if not normalized_input:
        raise ValueError("Missing project name.")

    for name in registry:
        if _normalize_lookup_token(name) == normalized_input:
            return name

    alias_matches: list[str] = []
    for name in registry:
        alias_tokens = {_normalize_lookup_token(alias) for alias in get_project_aliases(name, config)}
        if normalized_input in alias_tokens:
            alias_matches.append(name)
    if len(alias_matches) == 1:
        return alias_matches[0]
    if len(alias_matches) > 1:
        raise ValueError(f"Ambiguous project alias '{project_name}': {sorted(alias_matches)}")

    if not allow_fuzzy:
        raise ValueError(
            f"Project '{project_name}' not in config registry. Known projects: {list(registry.keys())}"
        )

    input_words = set(normalized_input.replace("-", " ").split())
    fuzzy_matches: list[str] = []
    for name in registry:
        tokens = [name, get_project_display_name(name, config), *get_project_aliases(name, config)]
        for token in tokens:
            normalized_token = _normalize_lookup_token(token)
            if not normalized_token:
                continue
            token_words = set(normalized_token.replace("-", " ").split())
            if not token_words:
                continue
            common_words = input_words & token_words
            if input_words <= token_words or token_words <= input_words:
                fuzzy_matches.append(name)
                break
            if common_words and len(common_words) >= min(len(input_words), len(token_words)) * 0.5:
                fuzzy_matches.append(name)
                break

    fuzzy_matches = sorted(set(fuzzy_matches))
    if len(fuzzy_matches) == 1:
        return fuzzy_matches[0]
    if len(fuzzy_matches) > 1:
        raise ValueError(f"Ambiguous project name '{project_name}': {fuzzy_matches}")

    raise ValueError(
        f"Project '{project_name}' not in config registry. Known projects: {list(registry.keys())}"
    )


def _registered_project_paths(config: dict[str, Any]) -> set[Path]:
    paths: set[Path] = set()
    for entry in get_project_registry(config).values():
        canonical_raw = entry.get("canonical_path")
        if not canonical_raw:
            continue
        canonical = _expand_path(canonical_raw)
        try:
            paths.add(canonical.resolve())
        except OSError:
            paths.add(canonical)
    return paths


def list_registered_projects(config: dict[str, Any] | None = None) -> list[str]:
    return sorted(get_project_registry(config).keys())


def resolve_project_path(project_name: str, config: dict[str, Any] | None = None) -> Path:
    if config is None:
        config = load_config()

    registry = get_project_registry(config)
    project_name = resolve_project_key(project_name, config)

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
        SKILL_RUNTIME_KEY: default_skill_runtime_payload(timestamp=now),
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


def get_skill_runtime(index: dict[str, Any] | None = None, index_path: Path | None = None) -> dict[str, Any]:
    if index is None:
        index = load_index(index_path)
    runtime = index.get(SKILL_RUNTIME_KEY, {})
    return runtime if isinstance(runtime, dict) else {}


def get_update_gate_status(
    deployed_version: str | None = None,
    index: dict[str, Any] | None = None,
    index_path: Path | None = None,
) -> dict[str, Any]:
    current_version = (deployed_version or ATTENTION_VERSION).strip()
    runtime = get_skill_runtime(index=index, index_path=index_path)
    compiled_version = str(runtime.get("compiled_version", "")).strip()
    needs_bootstrap = compiled_version != current_version

    if not compiled_version:
        reason = "No compiled skill version recorded in the control plane."
    elif needs_bootstrap:
        reason = (
            f"Compiled skill version is `{compiled_version}`, "
            f"but deployed skill version is `{current_version}`."
        )
    else:
        reason = ""

    message = (
        "*Attention Repo update bootstrap required*\n\n"
        f"Deployed version: `{current_version}`\n"
        f"Compiled version: `{compiled_version or 'missing'}`\n\n"
        f"{reason}\n"
        "Run `scripts/attention bootstrap-update` once to validate local memory and "
        "recompile the control-plane state for this version."
    ).strip()

    return {
        "required": needs_bootstrap,
        "deployed_version": current_version,
        "compiled_version": compiled_version,
        "reason": reason,
        "message": message,
    }


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


def infer_project_scope(canonical_path: str | Path, config: dict[str, Any] | None = None) -> str:
    if config is None:
        config = load_config()

    repo = _expand_path(canonical_path)
    roots = config.get("paths", {})
    for root in roots.get("default_scan_roots", []):
        if repo.parent == _expand_path(root):
            return "projects"

    optional_roots = roots.get("optional_scan_roots", {})
    for scope, raw_root in optional_roots.items():
        if isinstance(raw_root, str) and repo.parent == _expand_path(raw_root):
            return scope

    return "discovered"


def summarize_current_task(repo: Path) -> tuple[str, str]:
    task_path = repo / "CURRENT_TASK.md"
    if not task_path.exists():
        return "missing", ""
    text = task_path.read_text(encoding="utf-8", errors="replace")
    lowered = text.lower()
    sections: dict[str, list[str]] = {}
    current_section = ""
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("## "):
            current_section = line[3:].strip().lower()
            sections.setdefault(current_section, [])
            continue
        sections.setdefault(current_section, []).append(line)

    status = "idle"
    attention_lines = [
        line.strip().lower()
        for line in sections.get("attention state", []) + sections.get("attention", [])
        if line.strip()
    ]
    if any("released" in line for line in attention_lines):
        status = "released"
    elif any("blocked" in line for line in attention_lines):
        status = "blocked"
    elif any("paused" in line for line in attention_lines):
        status = "paused"
    elif any("wrapped" in line for line in attention_lines):
        status = "wrapped"
    elif "completed" in lowered:
        status = "completed"
    elif "in progress" in lowered or "active" in lowered:
        status = "active"

    status_lines = sections.get("status", [])
    has_status_summary = any(line.strip() for line in status_lines)
    if status == "released" and not has_status_summary:
        for raw_line in sections.get("attention state", []) + sections.get("attention", []):
            line = raw_line.strip()
            if line.lower().startswith("- note:"):
                return status, line.split(":", 1)[1].strip()[:240]

    summary = ""
    candidate_lines = status_lines if has_status_summary else text.splitlines()
    for raw_line in candidate_lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("<!--") or line.startswith("- State:"):
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
    *,
    scope: str | None = None,
    menu_visible: bool | None = None,
) -> dict[str, Any]:
    repo = _expand_path(canonical_path)
    record = dict(existing or {})
    record["canonical_path"] = str(repo)
    if scope:
        record["scope"] = scope
    if menu_visible is not None:
        record["menu_visible"] = menu_visible
    record["exists"] = repo.exists()
    record["has_map"] = (repo / "!MAP.md").exists()
    record["has_task"] = (repo / "CURRENT_TASK.md").exists()
    task_status, task_summary = summarize_current_task(repo)
    record["status"] = task_status
    record["task_summary"] = task_summary
    warnings: list[str] = []
    stale = False

    def parse_checkpoint(raw: Any) -> datetime | None:
        if not isinstance(raw, str) or not raw:
            return None
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))

    last_assemble = record.get("last_assemble")
    assemble_time = parse_checkpoint(last_assemble)
    freshness_time = parse_checkpoint(record.get("last_freshness"))
    sync_time = parse_checkpoint(record.get("last_sync_state"))
    recency_baseline = max(
        [checkpoint for checkpoint in (assemble_time, freshness_time, sync_time) if checkpoint is not None],
        default=None,
    )

    if recency_baseline is not None:
        if (datetime.now(timezone.utc) - recency_baseline).total_seconds() / 86400 > 7:
            stale = True
            warnings.append("No assemble/freshness/sync in 7+ days")
        map_path = repo / "!MAP.md"
        if map_path.exists():
            map_mtime = datetime.fromtimestamp(map_path.stat().st_mtime, tz=timezone.utc)
            if map_mtime > recency_baseline:
                stale = True
                warnings.append("!MAP.md modified since last verified/synced state")

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
    scope = existing.get("scope")
    menu_visible = existing.get("menu_visible")
    try:
        config = load_config()
        project = get_project_registry(config).get(project_name, {})
        scope = project.get("scope", scope) or infer_project_scope(canonical_path, config)
        menu_visible = project.get("menu_visible", menu_visible)
    except Exception as exc:
        print(f"[attention-repo] warning: could not load config in record_project_operation: {exc}", file=sys.stderr)
    record = refresh_project_record(
        project_name,
        canonical_path,
        existing,
        scope=scope,
        menu_visible=menu_visible,
    )
    record["last_operation"] = operation
    record["last_result"] = result
    record["last_event_at"] = utc_now()

    field_map = {
        "declare-intent": "last_declare_intent",
        "assemble": "last_assemble",
        "freshness": "last_freshness",
        "finalize-change": "last_finalize",
        "release-attention": "last_release_attention",
        "sync-state": "last_sync_state",
        "update-task": "last_update_task",
        "clear-task": "last_clear_task",
        "reinit": "last_reinit",
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
        projects[name] = refresh_project_record(
            name,
            entry["canonical_path"],
            index.get("projects", {}).get(name),
            scope=entry.get("scope") or infer_project_scope(entry["canonical_path"], config),
            menu_visible=entry.get("menu_visible", True),
        )
    index["projects"] = projects
    return save_index(index, index_path)


def register_project(
    config: dict[str, Any],
    project_name: str,
    canonical_path: str | Path,
    source: str = "discovered",
    managed: bool = True,
    *,
    aliases: list[str] | None = None,
    display_name: str | None = None,
    scope: str | None = None,
    menu_visible: bool = True,
) -> None:
    resolved_scope = scope or infer_project_scope(canonical_path, config)
    normalized_project = _normalize_lookup_token(project_name)
    filtered_aliases: list[str] = []
    for alias in aliases or []:
        alias_text = str(alias).strip()
        alias_token = _normalize_lookup_token(alias_text)
        if not alias_token or alias_token == normalized_project or alias_token in RESERVED_PROJECT_TOKENS:
            continue
        if alias_text not in filtered_aliases:
            filtered_aliases.append(alias_text)
    registry = get_project_registry(config)
    registry[project_name] = {
        "canonical_path": str(_expand_path(canonical_path)),
        "source_strategy": "local_only",
        "managed": managed,
        "source": source,
        "aliases": filtered_aliases,
        "display_name": (display_name or "").strip(),
        "scope": resolved_scope,
        "menu_visible": menu_visible,
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
    registered_paths = _registered_project_paths(config)
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
                    "registered": child.resolve() in registered_paths or child.name in registry,
                }
            )
    return candidates
