#!/usr/bin/env python3
"""
Service-aware router for attention_repo skill.

This is the core routing engine that connects user input (from Telegram, 
WhatsApp, TUI, or CLI) to the attention_repo CLI commands. It provides:

1. Natural language intent detection
2. Session-based conversation flow (for multi-turn interactions)
3. Persistent state tracking with staleness detection
4. Platform-agnostic responses formatted for each target

Architecture:
-----------
User Input → service_router.py → attention CLI → Response
                ↓
         Session State (in-memory)
         Persistent Index (~/.openclaw/attention-repo/index.json)

Telegram Flow:
-------------
/attention_repo → format_main_menu() → Inline keyboard with 3 actions
    ↓
[Click Projects] → Project selector
    ↓
[Click project] → Start flow with latest task summary
    ↓
[Reply with follow-up task] → execute_intent() → Run CLI → Update index

For the OpenClaw community:
- This is the main entry point for skill integration
- OpenClaw should call handle() and use message() tool with buttons for Telegram
- See SKILL.md for full integration guide

Author: OpenClaw Community
License: MIT
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from scripts.attention_state import get_state as get_global_attention_state
    from scripts.version_info import get_version
    from scripts.resolve import (
        detect_project_candidates,
        ensure_index as ensure_central_index,
        get_config_path,
        get_index_path,
        get_project_display_name,
        get_project_registry,
        get_update_gate_status,
        infer_project_scope,
        list_registered_projects as resolve_list_registered_projects,
        load_config as resolve_load_config,
        load_index as resolve_load_index,
        record_project_operation,
        register_project,
        reindex_registered_projects,
        refresh_project_record,
        resolve_project_key,
        resolve_project_name_from_path,
        resolve_project_path,
        save_config,
        summarize_current_task,
    )
except ModuleNotFoundError:
    from attention_state import get_state as get_global_attention_state
    from version_info import get_version
    from resolve import (
        detect_project_candidates,
        ensure_index as ensure_central_index,
        get_config_path,
        get_index_path,
        get_project_display_name,
        get_project_registry,
        get_update_gate_status,
        infer_project_scope,
        list_registered_projects as resolve_list_registered_projects,
        load_config as resolve_load_config,
        load_index as resolve_load_index,
        record_project_operation,
        register_project,
        reindex_registered_projects,
        refresh_project_record,
        resolve_project_key,
        resolve_project_name_from_path,
        resolve_project_path,
        save_config,
        summarize_current_task,
    )


SKILL_ROOT = Path(__file__).parent.parent
ATTENTION_CLI = SKILL_ROOT / "scripts" / "attention"


@dataclass
class RouteRequest:
    """Incoming request from any platform."""
    text: str                    # Raw input text
    user_id: str                 # Platform user ID
    platform: str                # 'telegram', 'whatsapp', 'tui', 'cli'
    chat_type: str = "direct"    # 'direct', 'group', 'channel'
    message_id: str | None = None
    reply_to: str | None = None


@dataclass  
class RouteResponse:
    """Response to be formatted by platform handler."""
    text: str
    structured_data: dict | None = None
    suggest_menu: bool = False
    menu_items: list[dict] | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Intent Detection
# ─────────────────────────────────────────────────────────────────────────────

INTENT_PATTERNS = {
    "projects": [
        r"list\s+(?:all\s+)?projects",
        r"what\s+projects\s+are\s+available",
        r"show\s+(?:me\s+)?(?:the\s+)?projects",
    ],
    "init": [
        r"init(?:ialize)?(?:\s+projects)?",
        r"index\s+new",
        r"scan\s+(?:for\s+)?projects",
    ],
    "reinit": [
        r"reinit\s+(.+?)(?:\s*$|\?)",
        r"repair\s+(.+?)(?:\s*$|\?)",
        r"recover\s+(.+?)(?:\s*$|\?)",
    ],
    "wrap": [
        r"wrap\s+(.+?)(?:\s*$|\?)",
        r"wrap\s*up\s+(.+?)(?:\s*$|\?)",
        r"finali[sz]e\s+(.+?)(?:\s*$|\?)",
        r"finish\s+(.+?)(?:\s*$|\?)",
    ],
    "start": [
        r"start\s+(.+?)(?:\s*$|\?)",
        r"open\s+(.+?)(?:\s*$|\?)",
        r"focus\s+on\s+(.+?)(?:\s*$|\?)",
    ],
}


def detect_intent(text: str) -> tuple[str | None, str | None]:
    """
    Detect intent and extract project from natural language.
    Returns: (intent, project_name or None)
    """
    text_lower = text.lower().strip()
    
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                project = None
                if match.groups():
                    try:
                        project = match.group(1).strip() if match.group(1) else None
                    except (IndexError, AttributeError):
                        project = None
                # Clean up project name (remove trailing punctuation)
                if project:
                    project = project.rstrip('?.!')
                return intent, project
    
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# Configuration & Resolution
# ─────────────────────────────────────────────────────────────────────────────

def _load_config() -> dict[str, Any]:
    """Load central attention-repo config (with legacy fallback handled by resolver)."""
    return resolve_load_config()


def list_projects() -> list[str]:
    """Return list of registered project names."""
    return resolve_list_registered_projects(_load_config())


def resolve_project(project_name: str) -> Path:
    """Resolve project path via config with alias-aware matching."""
    config = _load_config()
    canonical_key = resolve_project_key(project_name, config)
    registry = get_project_registry(config)
    return Path(registry[canonical_key]["canonical_path"])


def normalize_project_name(project_name: str) -> str:
    """Normalize project name to canonical case from config."""
    try:
        return resolve_project_key(project_name, _load_config())
    except ValueError:
        return project_name


def display_project_name(project_name: str) -> str:
    return get_project_display_name(project_name, _load_config())


def _format_attention_prefix(mode: str, project: str) -> str:
    display_name = display_project_name(project)
    if display_name != project:
        return f"`[{mode}@{display_name}]` (`{project}`)"
    return f"`[{mode}@{display_name}]`"


def _requires_confirmation(platform: str) -> bool:
    return platform in {"telegram", "tui"}


def _set_pending_confirmation(
    session: dict,
    *,
    action: str,
    project: str,
    task_text: str | None = None,
) -> None:
    session["pending_confirmation"] = {
        "action": action,
        "project": project,
        "task_text": task_text,
    }


def _clear_pending_confirmation(session: dict) -> None:
    session["pending_confirmation"] = None


def _restore_global_attention_session(session: dict) -> str | None:
    """Resume the active project from global attention state when in-memory session is gone."""
    state = get_global_attention_state()
    active_path = state.get("active_path")
    if not active_path:
        return None
    repo = Path(active_path).expanduser()
    project = resolve_project_name_from_path(repo, _load_config())
    if not project:
        return None
    session["selected_project"] = project
    session["active_project"] = project
    session["awaiting_followup"] = True
    return project


# ─────────────────────────────────────────────────────────────────────────────
# CLI Execution
# ─────────────────────────────────────────────────────────────────────────────

def run_cli(command: str, project: str, extra_args: list[str] | None = None) -> tuple[str, str, int]:
    """Run attention CLI command. Returns (stdout, stderr, rc)."""
    # Normalize project name to canonical case
    cmd = [str(ATTENTION_CLI), command]
    if project:
        canonical_project = normalize_project_name(project)
        cmd.append(canonical_project)
    if extra_args:
        cmd.extend(extra_args)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as e:
        return "", str(e), 1


# ─────────────────────────────────────────────────────────────────────────────
# Session State (in-memory for conversation flow)
# ─────────────────────────────────────────────────────────────────────────────

_user_sessions: dict[str, dict] = {}


def get_session(user_id: str) -> dict:
    """Get or create user session state."""
    if user_id not in _user_sessions:
        _user_sessions[user_id] = {
            "pending_intent": None,
            "selected_project": None,
            "active_project": None,
            "awaiting_followup": False,
            "awaiting_registration": False,
            "registration_candidates": [],
            "pending_confirmation": None,
        }
    return _user_sessions[user_id]


def clear_session(user_id: str):
    """Clear user session state."""
    _user_sessions.pop(user_id, None)


# ─────────────────────────────────────────────────────────────────────────────
# Persistent Index (State Tracking with Timestamps)
# ─────────────────────────────────────────────────────────────────────────────

ATTENTION_VERSION = get_version()
STALENESS_DAYS = 7  # Warn if not checked in 7 days


def _load_index() -> dict:
    """Load or create the central attention-repo index."""
    ensure_central_index()
    return resolve_load_index()


def _save_index(index: dict):
    """Save index to disk via central state helpers."""
    path = get_index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    index["last_updated"] = _now_iso()
    path.write_text(json.dumps(index, indent=2, default=str), encoding="utf-8")


def _now_iso() -> str:
    """Current timestamp in ISO format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(timestamp: str) -> "datetime":
    """Parse ISO timestamp."""
    from datetime import datetime, timezone
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def _days_since(timestamp: str) -> float:
    """Calculate days since timestamp."""
    from datetime import datetime, timezone
    then = _parse_iso(timestamp)
    now = datetime.now(timezone.utc)
    return (now - then).total_seconds() / 86400


def update_project_index(project: str, operation: str, result: str = "ok"):
    """Update index after an operation."""
    try:
        record_project_operation(project, resolve_project(project), operation, result=result)
    except Exception:
        index = _load_index()
        project_record = index.setdefault("projects", {}).setdefault(project, {})
        project_record["last_operation"] = operation
        project_record["last_result"] = result
        _save_index(index)


def _scope_icon(scope: str) -> str:
    return "📋" if scope == "projects" else "🧰" if scope == "skills" else "📦"


def _prepare_project_for_start(project: str) -> str | None:
    """Bootstrap missing templates on first open without changing task state."""
    staleness = get_project_staleness(project)
    if staleness.get("last_assemble"):
        return None

    repo = resolve_project(project)
    result = subprocess.run(
        [str(ATTENTION_CLI), "init", str(repo)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return f"Prep warning: {result.stderr or result.stdout}".strip()
    try:
        record_project_operation(project, repo, "init")
    except Exception:
        pass
    return "Prepared project memory for first use."


def _format_confirmation(action: str, project: str, request: RouteRequest, task_text: str | None = None) -> RouteResponse:
    display_name = display_project_name(project)
    lines = [_format_attention_prefix(f"confirm-{action}", project), ""]
    if action == "start":
        lines.append(f"Confirm focus on *{display_name}*?")
        if task_text:
            lines.append(f"Pending task: {task_text}")
            lines.append("On Yes: save the task and run `update-task -> assemble`.")
        else:
            lines.append("On Yes: open the repo focus view and wait for your next task.")
    elif action == "reinit":
        lines.append(f"Confirm recovery reinit for *{display_name}*?")
        lines.append("On Yes: archive broken files, rebuild safe templates, salvage readable task context, and auto-assemble only if the declaration is still valid.")
    else:
        lines.append(f"Confirm wrap and release attention for *{display_name}*?")
        lines.append("On Yes: run `map-freshness-check -> finalize-change -> sync-state -> release-attention`.")

    if request.platform == "tui":
        lines.append("")
        lines.append("Reply `y` to continue or `n` to cancel.")

    return RouteResponse(
        text="\n".join(lines),
        suggest_menu=request.platform == "telegram",
        menu_items=[
            {"label": "Yes", "action": f"confirm-{action}", "project": project, "row": 0},
            {"label": "No", "action": "cancel-confirmation", "project": project, "row": 0},
        ] if request.platform == "telegram" else None,
    )


def _request_confirmation_or_execute(
    intent: str,
    project: str,
    request: RouteRequest,
    *,
    task_text: str | None = None,
) -> RouteResponse:
    session = get_session(request.user_id)
    if _requires_confirmation(request.platform):
        _set_pending_confirmation(session, action=intent, project=project, task_text=task_text)
        return _format_confirmation(intent, project, request, task_text)
    return execute_intent(intent, project, request, task_text=task_text)


def _cancel_confirmation(request: RouteRequest, action: str | None, project: str | None) -> RouteResponse:
    if action == "start":
        response = format_index_menu(build_project_index(), request.platform)
        response.text = "\n".join(["Focus selection cancelled.", "", response.text])
        return response
    if action == "reinit" and project:
        response = format_start_focus(project)
        response.text = "\n".join(["Reinit cancelled. Repo state was not changed.", "", response.text])
        return response
    if action == "wrap" and project:
        response = format_start_focus(project)
        response.text = "\n".join(["Wrap cancelled. Attention remains on this repo.", "", response.text])
        return response
    return RouteResponse(text="Confirmation cancelled. Use /attention_repo to continue.")


def _scan_registration_candidates() -> list[dict[str, Any]]:
    config = _load_config()
    candidates = detect_project_candidates(config, include_skills=True)
    return sorted(
        candidates,
        key=lambda item: (0 if not item["registered"] else 1, item["scope"], item["name"].lower()),
    )


def _format_registration_scan(candidates: list[dict[str, Any]]) -> RouteResponse:
    total = len(candidates)
    registered = sum(1 for item in candidates if item["registered"])
    unregistered = total - registered
    new_candidates = [item for item in candidates if not item["registered"]]
    existing_candidates = [item for item in candidates if item["registered"]]
    lines = ["*Index New* — scanned repo roots\n"]
    lines.append(f"Found: {total} repo(s)")
    lines.append(f"Unregistered: {unregistered}")
    lines.append(f"Already registered: {registered}\n")

    if not new_candidates and not existing_candidates:
        lines.append("No repos found in the configured project or skills roots.")
    else:
        if new_candidates:
            lines.append("Unregistered repos:")
            for candidate in new_candidates:
                scope_icon = _scope_icon(candidate["scope"])
                lines.append(f"- {scope_icon} *{candidate['name']}* [{candidate['scope']}] — {candidate['classification']}")
        if existing_candidates:
            lines.append("\nAlready registered:")
            for candidate in existing_candidates:
                scope_icon = _scope_icon(candidate["scope"])
                lines.append(f"- {scope_icon} {candidate['name']}")
        lines.append("\nReply `register <project-name>`, `register all`, or `cancel`.")
        lines.append("Use the project name exactly as shown.")

    return RouteResponse(
        text="\n".join(lines),
        suggest_menu=True,
        menu_items=[
            {"label": "🔄 Rescan", "action": "init", "project": "", "row": 0},
            {"label": "📋 Projects", "action": "list-projects", "project": "", "row": 0},
        ],
    )


def _parse_registration_selection(text: str, candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str | None]:
    lowered = text.lower().strip()
    if lowered == "cancel":
        return [], "__cancel__"
    if lowered == "register all":
        selected = [item for item in candidates if not item["registered"]]
        return selected, None if selected else "Everything in this scan is already registered."
    if not lowered.startswith("register "):
        return [], "Reply with `register <project-name>`, `register all`, or `cancel`."

    requested_name = text.strip()[len("register "):].strip()
    if not requested_name:
        return [], "Missing project name. Use `register <project-name>`."

    for candidate in candidates:
        if candidate["name"].lower() == requested_name.lower():
            if candidate["registered"]:
                return [], f"`{candidate['name']}` is already registered in this scan."
            return [candidate], None

    available = ", ".join(sorted(item["name"] for item in candidates if not item["registered"]))
    return [], f"Unknown repo in current scan: `{requested_name}`.\nAvailable: {available}"


def _is_registration_reply(text: str) -> bool:
    lowered = text.lower().strip()
    return lowered == "cancel" or lowered == "register all" or lowered.startswith("register ")


def _register_selected_candidates(selected: list[dict[str, Any]], candidates: list[dict[str, Any]] | None = None) -> RouteResponse:
    config = _load_config()
    added: list[str] = []
    skipped: list[str] = []
    template_notes: list[str] = []

    for candidate in selected:
        name = candidate["name"]
        if candidate["registered"]:
            skipped.append(f"{name} (already registered)")
            continue
        register_project(
            config,
            name,
            candidate["canonical_path"],
            source=candidate["scope"],
            managed=True,
            scope=candidate["scope"],
        )
        repo = Path(candidate["canonical_path"])
        result = subprocess.run(
            [str(ATTENTION_CLI), "init", str(repo)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            template_notes.append(f"{name}: templates ready")
        else:
            template_notes.append(f"{name}: template warning: {result.stderr or result.stdout}".strip())
        added.append(name)
        candidate["registered"] = True

    if candidates:
        selected_names = {item["name"] for item in selected}
        for candidate in candidates:
            if candidate["name"] in selected_names:
                candidate["registered"] = True

    save_config(config)
    reindex_registered_projects(config)

    lines = ["*Register Projects*\n"]
    if added:
        lines.append("Registered:")
        for name in added:
            lines.append(f"- {name}")
    if skipped:
        lines.append("\nSkipped:")
        for item in skipped:
            lines.append(f"- {item}")
    if template_notes:
        lines.append("\nBootstrap:")
        for note in template_notes:
            lines.append(f"- {note}")
    if not added and not skipped:
        lines.append("Nothing changed.")
    if candidates:
        remaining = [item["name"] for item in candidates if not item["registered"]]
        if remaining:
            lines.append("\nStill available in this scan:")
            lines.append(", ".join(remaining))
            lines.append("Reply with `register <project-name>`, `register all`, or `cancel`.")

    return RouteResponse(
        text="\n".join(lines),
        suggest_menu=True,
        menu_items=[
            {"label": "📋 Projects", "action": "list-projects", "project": "", "row": 0},
            {"label": "🧭 Index New", "action": "init", "project": "", "row": 0},
        ],
    )


def get_project_staleness(project: str) -> dict:
    """Get staleness info for a project."""
    index = _load_index()
    proj_data = index.get("projects", {}).get(project, {})
    if proj_data.get("canonical_path"):
        proj_data = refresh_project_record(project, proj_data["canonical_path"], proj_data)

    staleness = {
        "last_assemble": proj_data.get("last_assemble"),
        "last_freshness": proj_data.get("last_freshness"),
        "days_since_assemble": None,
        "days_since_freshness": None,
        "is_stale": bool(proj_data.get("stale")),
        "warnings": list(proj_data.get("warnings", [])),
    }
    if staleness["last_assemble"]:
        staleness["days_since_assemble"] = _days_since(staleness["last_assemble"])
    if staleness["last_freshness"]:
        staleness["days_since_freshness"] = _days_since(staleness["last_freshness"])
    return staleness


# ─────────────────────────────────────────────────────────────────────────────
# Index / Menu Builder (Fast - no !MAP.md parsing)
# ─────────────────────────────────────────────────────────────────────────────

def build_project_index() -> list[dict]:
    """Build project index from the central config and index store."""
    config = _load_config()
    registry = get_project_registry(config)
    index_projects = _load_index().get("projects", {})
    projects = []
    for name, data in registry.items():
        if data.get("menu_visible", True) is False:
            continue
        cached = index_projects.get(name, {})
        scope = data.get("scope") or infer_project_scope(data.get("canonical_path", "unknown"), config)
        record = refresh_project_record(
            name,
            data.get("canonical_path", "unknown"),
            cached,
            scope=scope,
            menu_visible=data.get("menu_visible", True),
        )
        project_info = {
            "name": name,
            "display_name": get_project_display_name(name, config),
            "path": data.get("canonical_path", "unknown"),
            "scope": scope,
            "has_task": bool(record.get("has_task")),
            "entity_count": 0,
            "task_status": record.get("status", "idle"),
        }
        project_info["staleness"] = get_project_staleness(name)
        projects.append(project_info)
    return projects


def format_index_menu(projects: list[dict], platform: str) -> RouteResponse:
    """Format project picker for the start flow."""
    index = _load_index()
    
    lines = [f"*Projects* — choose a repo to start\n"]
    
    # Track if any stale projects
    stale_count = 0
    
    for p in projects:
        staleness = p.get("staleness", {})
        
        # Determine status emoji
        if staleness.get("is_stale"):
            status_emoji = "🔴"  # Stale
            stale_count += 1
        elif p.get("task_status") == "active":
            status_emoji = "🟢"
        elif p.get("task_status") == "completed":
            status_emoji = "✅"
        elif p.get("task_status") == "released":
            status_emoji = "⏹"
        else:
            status_emoji = "⚪"
        
        task_indicator = " 📝" if p["has_task"] else ""
        
        # Build detail line
        detail_parts = []
        if staleness.get("days_since_assemble") is not None:
            days = staleness["days_since_assemble"]
            detail_parts.append(f"refreshed {days:.0f}d ago")
        elif staleness.get("last_assemble"):
            detail_parts.append("recently refreshed")
        else:
            detail_parts.append("ready to open")
        
        if staleness.get("warnings"):
            detail_parts.append(f"⚠️ {len(staleness['warnings'])} warnings")
        
        detail_str = f" ({', '.join(detail_parts)})" if detail_parts else ""
        
        lines.append(f"{status_emoji} *{p['display_name']}*{task_indicator}{detail_str}")
    
    # Add footer based on state
    if stale_count > 0:
        lines.append(f"\n⚠️ *{stale_count} project(s) need attention*")
    else:
        lines.append(f"\n✅ All registered projects indexed")
        lines.append("_Last index update: " + index.get("last_updated", "unknown")[:10] + "_")
    
    lines.append("\n_Select a project to enter the start flow._")
    
    def project_sort_key(project: dict) -> tuple[int, int, str]:
        staleness = project.get("staleness", {})
        scope = project.get("scope", "projects")
        return (
            0 if staleness.get("is_stale") else 1,
            0 if scope == "projects" else 1,
            project["name"].lower(),
        )

    def project_label(project: dict) -> str:
        scope_icon = "📋" if project.get("scope", "projects") == "projects" else "🧰"
        stale_prefix = "🔴 " if project.get("staleness", {}).get("is_stale") else ""
        return f"{stale_prefix}{scope_icon} {project['display_name']}"

    # Build menu items - prioritize stale entries, keep projects ahead of skills, group into rows of 2
    menu_items = []
    row_num = 0
    for p in sorted(projects, key=project_sort_key):
        menu_items.append({
            "label": project_label(p),
            "action": "start",
            "project": p["name"],
            "row": row_num // 2,
        })
        row_num += 1
    
    return RouteResponse(
        text="\n".join(lines),
        suggest_menu=True,
        menu_items=menu_items
    )


def format_wrap_menu(projects: list[dict], platform: str) -> RouteResponse:
    """Format project picker for the wrap flow."""
    del platform
    lines = ["*Wrap Up* — choose a project to refresh memory and finalize state\n"]
    menu_items = []
    for idx, project in enumerate(projects):
        marker = "🔴" if project.get("staleness", {}).get("is_stale") else "📦"
        lines.append(f"{marker} *{project['display_name']}*")
        menu_items.append({
            "label": f"{marker} {project['display_name']}",
            "action": "wrap",
            "project": project["name"],
            "row": idx // 2,
        })
    return RouteResponse(text="\n".join(lines), suggest_menu=True, menu_items=menu_items)


def _read_task_excerpt(project: str) -> tuple[str, str]:
    """Return task status and a short task excerpt."""
    project_path = resolve_project(project)
    status, summary = summarize_current_task(project_path)
    if status == "missing":
        status = "idle"
    if summary:
        return status, summary
    task_path = project_path / "CURRENT_TASK.md"
    if not task_path.exists():
        return "idle", "No active task yet."
    content = task_path.read_text(encoding="utf-8", errors="replace").strip()
    excerpt = content[:280] if content else "No active task yet."
    return status, excerpt


def format_start_focus(project: str) -> RouteResponse:
    """Show latest project state and prompt for the next task."""
    prep_note = _prepare_project_for_start(project)
    staleness = get_project_staleness(project)
    status, task_excerpt = _read_task_excerpt(project)
    lines = [_format_attention_prefix("focus", project), ""]
    status_label = (
        "working" if status == "active"
        else "done" if status == "completed"
        else "released" if status == "released"
        else "ready"
    )
    lines.append(f"Current status: `{status_label}`")
    if prep_note:
        lines.append(prep_note)
    if staleness.get("is_stale"):
        warnings = ", ".join(staleness.get("warnings", [])) or "Index says project is stale."
        lines.append(f"Attention: {warnings}")
    lines.append("\nLast recorded focus:")
    lines.append(task_excerpt or "No active task yet.")
    lines.append("\nReply with what you want to work on next.")
    return RouteResponse(
        text="\n".join(lines),
        structured_data={"command": "start", "project": project, "status": status},
        suggest_menu=True,
        menu_items=[
            {"label": "💡 New Idea", "action": "new-idea", "project": project, "row": 0},
            {"label": "📋 List Others", "action": "list-projects", "project": "", "row": 0},
            {"label": "📦 Wrap Up", "action": "wrap", "project": project, "row": 1},
        ],
    )


def format_main_menu(platform: str) -> RouteResponse:
    """Show simplified top-level menu."""
    index = _load_index()
    
    # Check global attention state
    global_state = get_global_attention_state()
    active_attention = global_state.get("active")
    active_path = global_state.get("active_path", "")
    
    lines = [f"*Attention Repo* — v{ATTENTION_VERSION}\n"]
    
    # Show active attention if exists
    if active_attention:
        lines.append(f"📍 *Attending:* `{active_attention}`")
        lines.append(f"   Path: {active_path}")
    else:
        lines.append("📍 No active attention")
    
    lines.append(f"\nIndex updated: {index.get('last_updated', 'unknown')[:10]}")
    lines.append(f"Registered: {len(index.get('projects', {}))} project(s)\n")
    
    # Check for any stale projects
    config = _load_config()
    registry = get_project_registry(config)
    stale_count = 0
    for name in registry:
        staleness = get_project_staleness(name)
        if staleness.get("is_stale"):
            stale_count += 1
    
    if stale_count > 0:
        lines.append(f"⚠️ *{stale_count} project(s) stale*\n")
    
    lines.append("Select operation:")
    
    menu_items = [
        {"label": "📋 Projects", "action": "list-projects", "project": "", "row": 0},
        {"label": "🧭 Index New", "action": "init", "project": "", "row": 0},
        {"label": "📦 Wrap Up", "action": "menu-wrap", "project": "", "row": 1},
    ]
    
    return RouteResponse(
        text="\n".join(lines),
        suggest_menu=True,
        menu_items=menu_items
    )


def format_update_gate() -> RouteResponse:
    gate = get_update_gate_status(ATTENTION_VERSION, index=_load_index())
    lines = [
        "*Attention Repo update bootstrap required*",
        "",
        f"Deployed version: `{gate['deployed_version']}`",
        f"Compiled version: `{gate['compiled_version'] or 'missing'}`",
        "",
        gate["reason"] or "The control plane has not been compiled for this deployed skill yet.",
        "",
        "Run `bootstrap-update` once to validate local `!MAP.md` / `CURRENT_TASK.md` and unlock normal flows.",
    ]
    return RouteResponse(
        text="\n".join(lines),
        suggest_menu=True,
        menu_items=[
            {"label": "🛠 Compile Update", "action": "bootstrap-update", "project": "", "row": 0},
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Routing Logic
# ─────────────────────────────────────────────────────────────────────────────

def route(request: RouteRequest) -> RouteResponse:
    """
    Main router. Takes any request, returns response.
    Flow: Menu first → Intent declaration → !MAP.md check
    """
    text = request.text.strip()
    user_id = request.user_id
    session = get_session(user_id)
    ensure_central_index()
    lowered_input = text.lower().strip()

    try:
        _load_config()
    except FileNotFoundError:
        if text.startswith("attn:"):
            parts = text[5:].split(":")
            action = parts[0] if len(parts) > 0 else ""
            if action == "bootstrap-update":
                return execute_intent("bootstrap-update", "", request)
        if lowered_input == "bootstrap-update":
            return execute_intent("bootstrap-update", "", request)
        return RouteResponse(
            text=(
                "*Attention Repo setup required*\n\n"
                f"Config path: `{get_config_path()}`\n"
                f"Index path: `{get_index_path()}`\n\n"
                "Run `scripts/attention bootstrap-update` to create and compile the control plane, "
                "or `scripts/attention init-config` if you only want to create the central config first."
            )
        )

    gate = get_update_gate_status(ATTENTION_VERSION, index=_load_index())

    # Check for explicit command prefix (handle both dash and underscore variants)
    # Telegram converts /attention-repo to /attention_repo — underscore is canonical
    if text.startswith(("/attention_repo", "!attention_repo", "/attention-repo", "!attention-repo")):
        # Normalize TO underscore (canonical form)
        text = text.replace("attention-repo", "attention_repo")
        remainder = text.split(None, 1)[1] if " " in text else ""
        if not remainder:
            return format_update_gate() if gate["required"] else format_main_menu(request.platform)
        text = remainder

    lowered = text.lower().strip()
    if gate["required"]:
        if text.startswith("attn:"):
            parts = text[5:].split(":")
            action = parts[0] if len(parts) > 0 else ""
            if action == "bootstrap-update":
                return execute_intent("bootstrap-update", "", request)
        if lowered == "bootstrap-update":
            return execute_intent("bootstrap-update", "", request)
        return format_update_gate()

    if (
        session.get("awaiting_registration")
        and session.get("registration_candidates")
        and not text.startswith("attn:")
        and _is_registration_reply(text)
    ):
        selected, error = _parse_registration_selection(text, session["registration_candidates"])
        if error == "__cancel__":
            session["awaiting_registration"] = False
            session["registration_candidates"] = []
            return RouteResponse(text="Registration cancelled. Use /attention_repo to see the menu.")
        if error:
            return RouteResponse(text=error)
        response = _register_selected_candidates(selected, session["registration_candidates"])
        if any(not item["registered"] for item in session["registration_candidates"]):
            session["awaiting_registration"] = True
        else:
            session["awaiting_registration"] = False
            session["registration_candidates"] = []
        return response

    pending_confirmation = session.get("pending_confirmation") or {}
    if pending_confirmation and not text.startswith("attn:"):
        lowered_confirmation = text.lower().strip()
        if lowered_confirmation in {"y", "yes"}:
            action = str(pending_confirmation.get("action", "")).strip()
            project = str(pending_confirmation.get("project", "")).strip()
            task_text = pending_confirmation.get("task_text")
            _clear_pending_confirmation(session)
            return execute_intent(action, project, request, task_text=task_text)
        if lowered_confirmation in {"n", "no", "cancel"}:
            action = pending_confirmation.get("action")
            project = pending_confirmation.get("project")
            _clear_pending_confirmation(session)
            return _cancel_confirmation(request, action, project)

    # Recover focus from global attention state when Telegram/session memory is gone.
    if (
        not text.startswith("attn:")
        and not session.get("pending_confirmation")
        and not session.get("active_project")
    ):
        _restore_global_attention_session(session)

    # Follow-up task entry after start flow.
    if session.get("awaiting_followup") and session.get("active_project") and not text.startswith("attn:"):
        first_token = text.split()[0].lower() if text.split() else ""
        if first_token not in {"start", "init", "wrap", "projects", "/attention_repo", "/attention-repo"}:
            return execute_intent("start", session["active_project"], request, task_text=text)
    
    # Handle attn: prefixed callbacks (from inline buttons)
    if text.startswith("attn:"):
        parts = text[5:].split(":")  # Remove "attn:" prefix
        action = parts[0] if len(parts) > 0 else ""
        project = parts[1] if len(parts) > 1 else ""
        canonical_project = normalize_project_name(project) if project else ""

        if action == "cancel":
            session["pending_intent"] = None
            session["awaiting_followup"] = False
            _clear_pending_confirmation(session)
            return RouteResponse(text="Cancelled. Use /attention_repo to see the menu.")
        if action == "cancel-confirmation":
            pending = session.get("pending_confirmation") or {}
            _clear_pending_confirmation(session)
            return _cancel_confirmation(request, pending.get("action"), pending.get("project"))
        if action == "list-projects":
            projects = build_project_index()
            return format_index_menu(projects, request.platform)
        if action == "menu-wrap":
            return format_wrap_menu(build_project_index(), request.platform)
        if action == "init":
            return execute_intent("init", "", request)
        if action == "confirm-start" and canonical_project:
            pending = session.get("pending_confirmation") or {}
            task_text = pending.get("task_text")
            _clear_pending_confirmation(session)
            return execute_intent("start", canonical_project, request, task_text=task_text)
        if action == "confirm-reinit" and canonical_project:
            _clear_pending_confirmation(session)
            return execute_intent("reinit", canonical_project, request)
        if action == "confirm-wrap" and canonical_project:
            _clear_pending_confirmation(session)
            return execute_intent("wrap", canonical_project, request)
        if action == "start" and canonical_project:
            return _request_confirmation_or_execute("start", canonical_project, request)
        if action == "new-idea" and canonical_project:
            # New idea - prompt for task text then confirm
            session = get_session(request.user_id)
            session["selected_project"] = canonical_project
            session["active_project"] = canonical_project
            session["awaiting_followup"] = True
            _set_pending_confirmation(session, action="start", project=canonical_project)
            lines = [
                _format_attention_prefix("new-idea", canonical_project),
                "",
                f"Enter your new idea or task for *{display_project_name(canonical_project)}*.",
                "",
                "Reply with what you want to work on — I'll save it as the new task and start working.",
            ]
            return RouteResponse(
                text="\n".join(lines),
                suggest_menu=True,
                menu_items=[
                    {"label": "← Back", "action": "start", "project": canonical_project, "row": 0},
                ],
            )
        if action == "reinit" and canonical_project:
            return _request_confirmation_or_execute("reinit", canonical_project, request)
        if action == "wrap" and canonical_project:
            return _request_confirmation_or_execute("wrap", canonical_project, request)

    if lowered == "projects":
        return format_index_menu(build_project_index(), request.platform)
    if lowered == "init":
        return execute_intent("init", "", request)
    if lowered.startswith("reinit "):
        project = text.split(None, 1)[1].strip()
        return _request_confirmation_or_execute("reinit", normalize_project_name(project), request)
    if lowered == "wrap":
        return format_wrap_menu(build_project_index(), request.platform)
    if lowered.startswith("wrap "):
        project = text.split(None, 1)[1].strip()
        return _request_confirmation_or_execute("wrap", normalize_project_name(project), request)
    if lowered.startswith("start "):
        parts = text.split(None, 2)
        if len(parts) < 2:
            return RouteResponse(text="Usage: /attention_repo start <project> [task]")
        project = normalize_project_name(parts[1])
        task_text = parts[2].strip() if len(parts) > 2 else None
        return _request_confirmation_or_execute("start", project, request, task_text=task_text)
    
    # Detect intent
    intent, project = detect_intent(text)
    
    if not intent:
        return format_main_menu(request.platform)

    if intent == "projects":
        return format_index_menu(build_project_index(), request.platform)
    if intent == "init":
        return execute_intent("init", "", request)
    if intent in {"start", "reinit", "wrap"} and project:
        return _request_confirmation_or_execute(intent, normalize_project_name(project), request)

    return format_main_menu(request.platform)


def execute_intent(intent: str, project: str, request: RouteRequest, task_text: str | None = None) -> RouteResponse:
    """Execute the simplified start/init/wrap intent surface."""
    try:
        session = get_session(request.user_id)

        if intent == "bootstrap-update":
            stdout, stderr, rc = run_cli("bootstrap-update", "")
            if rc != 0:
                return RouteResponse(
                    text=(
                        "*Attention Repo update bootstrap failed*\n\n"
                        f"{stderr or stdout}"
                    ),
                    structured_data={"command": "bootstrap-update", "rc": rc},
                    suggest_menu=True,
                    menu_items=[
                        {"label": "🛠 Retry Compile", "action": "bootstrap-update", "project": "", "row": 0},
                    ],
                )
            lines = [
                "*Attention Repo update bootstrap complete*",
                "",
                stdout.strip() or "Control plane compiled for the deployed version.",
                "",
                "Normal flows are unlocked.",
            ]
            return RouteResponse(
                text="\n".join(lines),
                structured_data={"command": "bootstrap-update", "rc": 0},
                suggest_menu=True,
                menu_items=[
                    {"label": "📋 Projects", "action": "list-projects", "project": "", "row": 0},
                    {"label": "🧭 Index New", "action": "init", "project": "", "row": 0},
                ],
            )

        if intent == "init":
            session["awaiting_registration"] = True
            session["registration_candidates"] = _scan_registration_candidates()
            return _format_registration_scan(session["registration_candidates"])

        if not project:
            return RouteResponse(text=f"Missing project for `{intent}`. Use /attention_repo to browse projects.")

        if intent == "start":
            session["selected_project"] = project
            session["active_project"] = project
            session["awaiting_followup"] = True
            if task_text:
                task_stdout, task_stderr, task_rc = run_cli(
                    "update-task", project, ["--status-markdown", task_text]
                )
                if task_rc != 0:
                    return RouteResponse(text=f"Error updating task: {task_stderr or task_stdout}")
                assemble_stdout, assemble_stderr, assemble_rc = run_cli("assemble", project)
                if assemble_rc != 0:
                    return RouteResponse(text=f"Task saved for {project}, but assemble failed:\n{assemble_stderr or assemble_stdout}")
                status, latest_summary = _read_task_excerpt(project)
                lines = [
                    _format_attention_prefix("work", project),
                    "",
                    "Saved your focus and refreshed project context.",
                    f"Latest task: {latest_summary or task_text}",
                    "",
                    "Reply with another follow-up if the task changes.",
                ]
                return RouteResponse(
                    text="\n".join(lines),
                    structured_data={"command": "start", "project": project, "rc": 0, "status": status},
                    suggest_menu=True,
                    menu_items=[
                        {"label": "📦 Wrap Up", "action": "wrap", "project": project, "row": 0},
                        {"label": "📋 Projects", "action": "list-projects", "project": "", "row": 0},
                    ],
                )
            return format_start_focus(project)

        if intent == "reinit":
            session["awaiting_followup"] = False
            session["active_project"] = None
            reinit_stdout, reinit_stderr, reinit_rc = run_cli("reinit", project)
            if reinit_rc != 0:
                return RouteResponse(
                    text=(
                        f"{_format_attention_prefix('reinit-blocked', project)}\n\n"
                        f"Reinit failed:\n{reinit_stderr or reinit_stdout}"
                    ),
                    structured_data={"command": "reinit", "project": project, "rc": reinit_rc},
                )
            return RouteResponse(
                text="\n".join([
                    _format_attention_prefix("reinit", project),
                    "",
                    reinit_stdout.strip() or "Reinit completed.",
                ]),
                structured_data={"command": "reinit", "project": project, "rc": 0},
                suggest_menu=True,
                menu_items=[
                    {"label": "📋 Projects", "action": "list-projects", "project": "", "row": 0},
                    {"label": "▶ Start Again", "action": "start", "project": project, "row": 0},
                ],
            )

        if intent == "wrap":
            freshness_stdout, freshness_stderr, freshness_rc = run_cli("map-freshness-check", project)
            if freshness_rc != 0:
                return RouteResponse(
                    text=(
                        f"{_format_attention_prefix('wrap-blocked', project)}\n\n"
                        f"Freshness check failed:\n{freshness_stderr or freshness_stdout}"
                    ),
                    structured_data={"command": "wrap", "project": project, "rc": freshness_rc},
                )
            finalize_stdout, finalize_stderr, finalize_rc = run_cli(
                "finalize-change",
                project,
                ["--tests-result", "not_run", "--notes", "Wrapped via service_router"],
            )
            if finalize_rc != 0:
                return RouteResponse(
                    text=(
                        f"{_format_attention_prefix('wrap-blocked', project)}\n\n"
                        f"Freshness passed, but finalize failed:\n{finalize_stderr or finalize_stdout}"
                    ),
                    structured_data={"command": "wrap", "project": project, "rc": finalize_rc},
                )
            sync_stdout, sync_stderr, sync_rc = run_cli(
                "sync-state",
                project,
                ["--description", "Wrap-up sync via service_router"],
            )
            release_stdout, release_stderr, release_rc = run_cli(
                "release-attention",
                project,
                ["--note", "Released via service_router wrap flow"],
            )
            session["awaiting_followup"] = False
            session["active_project"] = None
            lines = [
                _format_attention_prefix("released", project),
                "",
                freshness_stdout.strip() or "Freshness check passed.",
                finalize_stdout.strip() or "Finalize report written.",
            ]
            if sync_rc == 0:
                lines.append(sync_stdout.strip() or "Project memory synced.")
            else:
                lines.append(f"Sync warning: {sync_stderr or sync_stdout}")
            if release_rc == 0:
                lines.append(release_stdout.strip() or "Attention released.")
            else:
                lines.append(f"Release warning: {release_stderr or release_stdout}")
            return RouteResponse(
                text="\n\n".join(lines),
                structured_data={"command": "wrap", "project": project, "rc": 0},
                suggest_menu=True,
                menu_items=[
                    {"label": "📋 Projects", "action": "list-projects", "project": "", "row": 0},
                    {"label": "▶ Start Again", "action": "start", "project": project, "row": 0},
                ],
            )
        return RouteResponse(text=f"Intent '{intent}' not yet implemented")
    except Exception as e:
        return RouteResponse(text=f"Error executing {intent}: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Platform Formatters
# ─────────────────────────────────────────────────────────────────────────────

def format_for_telegram(response: RouteResponse) -> dict:
    """Format response for Telegram with support for row-based buttons."""
    result = {
        "text": response.text,
        "parse_mode": "Markdown"
    }
    
    if response.suggest_menu and response.menu_items:
        # Build inline keyboard for Telegram
        # Supports row grouping via 'row' field in menu_items
        keyboard = []
        current_row = []
        current_row_num = 0
        
        for item in response.menu_items:
            callback = f"attn:{item.get('action')}:{item.get('project', '')}"
            button = {"text": item["label"], "callback_data": callback}
            
            # Check if item specifies a row
            item_row = item.get("row", None)
            
            if item_row is not None:
                # Explicit row grouping
                if item_row != current_row_num:
                    if current_row:
                        keyboard.append(current_row)
                    current_row = [button]
                    current_row_num = item_row
                else:
                    current_row.append(button)
            else:
                # Auto-group: if current row has <2 items, add to it
                if len(current_row) < 2:
                    current_row.append(button)
                else:
                    if current_row:
                        keyboard.append(current_row)
                    current_row = [button]
        
        # Don't forget the last row
        if current_row:
            keyboard.append(current_row)
        
        result["reply_markup"] = {"inline_keyboard": keyboard}
    
    return result


def format_for_whatsapp(response: RouteResponse) -> dict:
    """Format response for WhatsApp (no rich formatting)."""
    text = response.text.replace("**", "*")  # WhatsApp uses *bold*
    
    if response.suggest_menu and response.menu_items:
        text += "\n\nOptions:\n"
        for i, item in enumerate(response.menu_items, 1):
            text += f"{i}. {item['label']}\n"
    
    return {"text": text}


def format_for_tui(response: RouteResponse) -> dict:
    """Format response for TUI (rich text, no interactivity limits)."""
    return {
        "text": response.text,
        "structured": response.structured_data,
        "menu": response.menu_items if response.suggest_menu else None
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def handle(request: RouteRequest) -> dict:
    """
    Universal entry point. Returns platform-appropriate response.
    
    Usage:
        from service_router import handle, RouteRequest
        
        result = handle(RouteRequest(
            text="assemble summon-A2A-academy",
            user_id="user-123",
            platform="telegram"
        ))
        # Returns dict formatted for Telegram
    """
    response = route(request)
    
    # Format based on platform
    if request.platform == "telegram":
        return format_for_telegram(response)
    elif request.platform == "whatsapp":
        return format_for_whatsapp(response)
    elif request.platform == "tui":
        return format_for_tui(response)
    else:
        return {"text": response.text, "platform": request.platform}


# ─────────────────────────────────────────────────────────────────────────────
# CLI for testing
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: service_router.py <platform> '<text>'")
        print("Platforms: telegram, whatsapp, tui, cli")
        print()
        print("Examples:")
        print("  python3 service_router.py telegram 'assemble summon-A2A-academy'")
        print("  python3 service_router.py whatsapp 'show me the status of summon'")
        print("  python3 service_router.py tui 'declare intent for attention_repo'")
        sys.exit(1)
    
    platform = sys.argv[1]
    text = sys.argv[2]
    
    request = RouteRequest(
        text=text,
        user_id="test-user",
        platform=platform
    )
    
    result = handle(request)
    print(json.dumps(result, indent=2))
