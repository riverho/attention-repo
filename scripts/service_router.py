#!/usr/bin/env python3
"""
Service-aware router for attention_layer skill (v0.3.0).

This is the core routing engine that connects user input (from Telegram, 
WhatsApp, TUI, or CLI) to the attention_layer CLI commands. It provides:

1. Natural language intent detection
2. Session-based conversation flow (for multi-turn interactions)
3. Persistent state tracking with staleness detection
4. Platform-agnostic responses formatted for each target

Architecture:
-----------
User Input → service_router.py → attention CLI → Response
                ↓
         Session State (in-memory)
         Persistent Index (~/.openclaw/attention-layer/index.json)

Telegram Flow:
-------------
/attention_layer → format_main_menu() → Inline keyboard with 3 actions
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

Version: 0.3.0
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
    from scripts.resolve import (
        ensure_index as ensure_central_index,
        get_config_path,
        get_index_path,
        get_project_registry,
        list_registered_projects as resolve_list_registered_projects,
        load_config as resolve_load_config,
        load_index as resolve_load_index,
        record_project_operation,
        refresh_project_record,
        resolve_project_path,
        summarize_current_task,
    )
except ModuleNotFoundError:
    from resolve import (
        ensure_index as ensure_central_index,
        get_config_path,
        get_index_path,
        get_project_registry,
        list_registered_projects as resolve_list_registered_projects,
        load_config as resolve_load_config,
        load_index as resolve_load_index,
        record_project_operation,
        refresh_project_record,
        resolve_project_path,
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
    """Load central attention-layer config (with legacy fallback handled by resolver)."""
    return resolve_load_config()


def list_projects() -> list[str]:
    """Return list of registered project names."""
    return resolve_list_registered_projects(_load_config())


def resolve_project(project_name: str) -> Path:
    """Resolve project path via config with fuzzy matching."""
    config = _load_config()
    registry = get_project_registry(config)
    
    # Normalize input
    normalized_input = project_name.lower().replace('-', ' ').replace('_', ' ')
    
    # Exact match first (case-insensitive)
    for name, data in registry.items():
        if name.lower() == project_name.lower():
            return Path(data["canonical_path"])
    
    # Fuzzy match - check if all words in input are in project name
    input_words = set(normalized_input.split())
    for name in registry:
        normalized_name = name.lower().replace('-', ' ').replace('_', ' ')
        name_words = set(normalized_name.split())
        
        # Check if input words are subset of name words or vice versa
        if input_words <= name_words or name_words <= input_words:
            return Path(registry[name]["canonical_path"])
        
        # Check for significant overlap
        common_words = input_words & name_words
        if len(common_words) >= min(len(input_words), len(name_words)) * 0.5:
            return Path(registry[name]["canonical_path"])
    
    raise ValueError(f"Unknown project: {project_name}")


def normalize_project_name(project_name: str) -> str:
    """Normalize project name to canonical case from config."""
    config = _load_config()
    registry = get_project_registry(config)
    
    # Normalize input
    normalized_input = project_name.lower().replace('-', ' ').replace('_', ' ')
    
    # Exact match (case-insensitive)
    for name in registry:
        if name.lower() == project_name.lower():
            return name
    
    # Fuzzy match with word overlap
    input_words = set(normalized_input.split())
    for name in registry:
        normalized_name = name.lower().replace('-', ' ').replace('_', ' ')
        name_words = set(normalized_name.split())
        
        if input_words <= name_words or name_words <= input_words:
            return name
        
        common_words = input_words & name_words
        if len(common_words) >= min(len(input_words), len(name_words)) * 0.5:
            return name
    
    return project_name  # Return as-is if no match


# ─────────────────────────────────────────────────────────────────────────────
# CLI Execution
# ─────────────────────────────────────────────────────────────────────────────

def run_cli(command: str, project: str, extra_args: list[str] | None = None) -> tuple[str, str, int]:
    """Run attention CLI command. Returns (stdout, stderr, rc)."""
    # Normalize project name to canonical case
    canonical_project = normalize_project_name(project)
    cmd = [str(ATTENTION_CLI), command, canonical_project]
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
        }
    return _user_sessions[user_id]


def clear_session(user_id: str):
    """Clear user session state."""
    _user_sessions.pop(user_id, None)


# ─────────────────────────────────────────────────────────────────────────────
# Persistent Index (State Tracking with Timestamps)
# ─────────────────────────────────────────────────────────────────────────────

ATTENTION_VERSION = "0.3.0"
STALENESS_DAYS = 7  # Warn if not checked in 7 days


def _load_index() -> dict:
    """Load or create the central attention-layer index."""
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
        cached = index_projects.get(name, {})
        record = refresh_project_record(name, data.get("canonical_path", "unknown"), cached) if not cached else cached
        project_info = {
            "name": name,
            "path": data.get("canonical_path", "unknown"),
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
        else:
            status_emoji = "⚪"
        
        task_indicator = " 📝" if p["has_task"] else ""
        
        # Build detail line
        detail_parts = []
        if staleness.get("days_since_assemble") is not None:
            days = staleness["days_since_assemble"]
            detail_parts.append(f"assembled {days:.0f}d ago")
        elif staleness.get("last_assemble"):
            detail_parts.append("assembled recently")
        else:
            detail_parts.append("never assembled")
        
        if staleness.get("warnings"):
            detail_parts.append(f"⚠️ {len(staleness['warnings'])} warnings")
        
        detail_str = f" ({', '.join(detail_parts)})" if detail_parts else ""
        
        lines.append(f"{status_emoji} *{p['name']}*{task_indicator}{detail_str}")
    
    # Add footer based on state
    if stale_count > 0:
        lines.append(f"\n⚠️ *{stale_count} project(s) need attention*")
    else:
        lines.append(f"\n✅ All registered projects indexed")
        lines.append("_Last index update: " + index.get("last_updated", "unknown")[:10] + "_")
    
    lines.append("\n_Select a project to enter the start flow._")
    
    # Build menu items - prioritize stale projects, group into rows of 2
    menu_items = []
    row_num = 0
    
    # First add stale projects
    for p in projects:
        if p.get("staleness", {}).get("is_stale"):
            menu_items.append({
                "label": f"🔴 {p['name']}",
                "action": "start",
                "project": p["name"],
                "row": row_num // 2  # 2 buttons per row
            })
            row_num += 1
    
    # Then add others
    for p in projects:
        if not p.get("staleness", {}).get("is_stale"):
            menu_items.append({
                "label": f"📋 {p['name']}",
                "action": "start",
                "project": p["name"],
                "row": row_num // 2  # 2 buttons per row
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
        lines.append(f"{marker} *{project['name']}*")
        menu_items.append({
            "label": f"{marker} {project['name']}",
            "action": "wrap",
            "project": project["name"],
            "row": idx // 2,
        })
    return RouteResponse(text="\n".join(lines), suggest_menu=True, menu_items=menu_items)


def _read_task_excerpt(project: str) -> tuple[str, str]:
    """Return task status and a short task excerpt."""
    project_path = resolve_project(project)
    status, summary = summarize_current_task(project_path)
    if summary:
        return status, summary
    task_path = project_path / "CURRENT_TASK.md"
    if not task_path.exists():
        return "missing", "No CURRENT_TASK.md yet."
    content = task_path.read_text(encoding="utf-8", errors="replace").strip()
    excerpt = content[:280] if content else "CURRENT_TASK.md is empty."
    return status, excerpt


def format_start_focus(project: str) -> RouteResponse:
    """Show latest project state and prompt for the next task."""
    staleness = get_project_staleness(project)
    status, task_excerpt = _read_task_excerpt(project)
    lines = [f"*Start {project}*\n"]
    lines.append(f"Current status: `{status}`")
    if staleness.get("is_stale"):
        warnings = ", ".join(staleness.get("warnings", [])) or "Index says project is stale."
        lines.append(f"Attention: {warnings}")
    lines.append("\nLatest task summary:")
    lines.append(task_excerpt or "No prior task summary recorded.")
    lines.append(
        "\nReply with the next task or change request to declare the current focus. "
        f"Example: `/attention_layer start {project} fix auth callback redirect`"
    )
    return RouteResponse(
        text="\n".join(lines),
        structured_data={"command": "start", "project": project, "status": status},
        suggest_menu=True,
        menu_items=[
            {"label": "📋 Projects", "action": "list-projects", "project": "", "row": 0},
            {"label": "📦 Wrap Up", "action": "wrap", "project": project, "row": 0},
        ],
    )


def format_main_menu(platform: str) -> RouteResponse:
    """Show simplified top-level menu."""
    index = _load_index()
    
    lines = [f"*Attention Layer* — v{ATTENTION_VERSION}\n"]
    lines.append(f"Index updated: {index.get('last_updated', 'unknown')[:10]}")
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

    try:
        _load_config()
    except FileNotFoundError:
        return RouteResponse(
            text=(
                "*Attention Layer setup required*\n\n"
                f"Config path: `{get_config_path()}`\n"
                f"Index path: `{get_index_path()}`\n\n"
                "Run `scripts/attention init-config` to create the central config, or "
                "`scripts/attention init --dry-run` to scan default project folders first."
            )
        )

    # Check for explicit command prefix (handle both dash and underscore variants)
    # Telegram converts /attention-layer to /attention_layer — underscore is canonical
    if text.startswith(("/attention_layer", "!attention_layer", "/attention-layer", "!attention-layer")):
        # Normalize TO underscore (canonical form)
        text = text.replace("attention-layer", "attention_layer")
        remainder = text.split(None, 1)[1] if " " in text else ""
        if not remainder:
            # Bare /attention_layer command - show main menu (not just projects)
            return format_main_menu(request.platform)
        text = remainder

    # Follow-up task entry after start flow.
    if session.get("awaiting_followup") and session.get("active_project") and not text.startswith("attn:"):
        first_token = text.split()[0].lower() if text.split() else ""
        if first_token not in {"start", "init", "wrap", "projects", "/attention_layer", "/attention-layer"}:
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
            return RouteResponse(text="Cancelled. Use /attention_layer to see the menu.")
        if action == "list-projects":
            projects = build_project_index()
            return format_index_menu(projects, request.platform)
        if action == "menu-wrap":
            return format_wrap_menu(build_project_index(), request.platform)
        if action == "init":
            return execute_intent("init", "", request)
        if action == "start" and canonical_project:
            return execute_intent("start", canonical_project, request)
        if action == "wrap" and canonical_project:
            return execute_intent("wrap", canonical_project, request)

    lowered = text.lower().strip()
    if lowered == "projects":
        return format_index_menu(build_project_index(), request.platform)
    if lowered == "init":
        return execute_intent("init", "", request)
    if lowered == "wrap":
        return format_wrap_menu(build_project_index(), request.platform)
    if lowered.startswith("wrap "):
        project = text.split(None, 1)[1].strip()
        return execute_intent("wrap", normalize_project_name(project), request)
    if lowered.startswith("start "):
        parts = text.split(None, 2)
        if len(parts) < 2:
            return RouteResponse(text="Usage: /attention_layer start <project> [task]")
        project = normalize_project_name(parts[1])
        task_text = parts[2].strip() if len(parts) > 2 else None
        return execute_intent("start", project, request, task_text=task_text)
    
    # Detect intent
    intent, project = detect_intent(text)
    
    if not intent:
        return format_main_menu(request.platform)

    if intent == "projects":
        return format_index_menu(build_project_index(), request.platform)
    if intent == "init":
        return execute_intent("init", "", request)
    if intent in {"start", "wrap"} and project:
        return execute_intent(intent, normalize_project_name(project), request)

    return format_main_menu(request.platform)


def execute_intent(intent: str, project: str, request: RouteRequest, task_text: str | None = None) -> RouteResponse:
    """Execute the simplified start/init/wrap intent surface."""
    try:
        session = get_session(request.user_id)

        if intent == "init":
            result = subprocess.run(
                [str(ATTENTION_CLI), "init"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            return RouteResponse(
                text=(result.stdout if result.returncode == 0 else result.stderr or result.stdout).strip() or "Project index refreshed.",
                structured_data={"command": "init", "rc": result.returncode},
                suggest_menu=True,
                menu_items=[
                    {"label": "📋 Projects", "action": "list-projects", "project": "", "row": 0},
                    {"label": "📦 Wrap Up", "action": "menu-wrap", "project": "", "row": 0},
                ],
            )

        if not project:
            return RouteResponse(text=f"Missing project for `{intent}`. Use /attention_layer to browse projects.")

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
                    f"*Start {project}*",
                    "",
                    "Declared current focus and refreshed the project map.",
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

        if intent == "wrap":
            session["awaiting_followup"] = False
            session["active_project"] = None
            freshness_stdout, freshness_stderr, freshness_rc = run_cli("map-freshness-check", project)
            if freshness_rc != 0:
                return RouteResponse(
                    text=f"Wrap blocked for {project}.\n\nFreshness check failed:\n{freshness_stderr or freshness_stdout}",
                    structured_data={"command": "wrap", "project": project, "rc": freshness_rc},
                )
            finalize_stdout, finalize_stderr, finalize_rc = run_cli(
                "finalize-change",
                project,
                ["--tests-result", "not_run", "--notes", "Wrapped via service_router"],
            )
            if finalize_rc != 0:
                return RouteResponse(
                    text=f"Freshness passed for {project}, but finalize failed:\n{finalize_stderr or finalize_stdout}",
                    structured_data={"command": "wrap", "project": project, "rc": finalize_rc},
                )
            sync_stdout, sync_stderr, sync_rc = run_cli(
                "sync-state",
                project,
                ["--description", "Wrap-up sync via service_router"],
            )
            lines = [
                f"*Wrap Up {project}*",
                "",
                freshness_stdout.strip() or "Freshness check passed.",
                finalize_stdout.strip() or "Finalize report written.",
            ]
            if sync_rc == 0:
                lines.append(sync_stdout.strip() or "Project memory synced.")
            else:
                lines.append(f"Sync warning: {sync_stderr or sync_stdout}")
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
        print("  python3 service_router.py tui 'declare intent for attention_layer'")
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
