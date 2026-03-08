#!/usr/bin/env python3
"""
Service-aware router for attention-layer skill (v3.2.4).

This is the core routing engine that connects user input (from Telegram, 
WhatsApp, TUI, or CLI) to the attention-layer CLI commands. It provides:

1. Natural language intent detection
2. Session-based conversation flow (for multi-turn interactions)
3. Persistent state tracking with staleness detection
4. Platform-agnostic responses formatted for each target

Architecture:
-----------
User Input → service_router.py → attention CLI → Response
                ↓
         Session State (in-memory)
         Persistent Index (.attention/index.json)

Telegram Flow:
-------------
/attention → format_main_menu() → Inline keyboard with 6 actions
    ↓
[Click action] → Project selector
    ↓
[Click project] → Confirmation dialog
    ↓
[Confirm] → execute_intent() → Run CLI → Update index

For the OpenClaw community:
- This is the main entry point for skill integration
- OpenClaw should call handle() and use message() tool with buttons for Telegram
- See SKILL.md for full integration guide

Version: 3.2.4
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


SKILL_ROOT = Path(__file__).parent.parent
ATTENTION_CONFIG = SKILL_ROOT / "attention-config.json"
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
    "assemble": [
        r"assemble\s+(.+?)(?:\s*$|\?)",
        r"show\s+(?:me\s+)?(?:the\s+)?(?:architecture|map)(?:\s+for)?\s+(.+?)(?:\s*$|\?)",
        r"what\s+is\s+the\s+state\s+of\s+(.+?)(?:\s*$|\?)",
    ],
    "freshness": [
        r"freshness(?:\s+check)?\s+(.+?)(?:\s*$|\?)",
        r"check\s+(?:the\s+)?freshness(?:\s+for)?\s+(.+?)(?:\s*$|\?)",
        r"is\s+(.+?)\s+up\s*to\s*date",
        r"verify\s+(.+?)(?:\s*$|\s+has\s+)",
    ],
    "status": [
        r"status(?:\s+of)?\s+(.+?)(?:\s*$|\?)",
        r"what\s+is\s+the\s+current\s+task(?:\s+for)?\s+(.+?)(?:\s*$|\?)",
        r"show\s+(?:me\s+)?(?:the\s+)?task(?:\s+for)?\s+(.+?)(?:\s*$|\?)",
    ],
    "declare-intent": [
        r"declare\s+(?:intent\s+)?(?:for\s+)?(.+?)(?:\s*$|\?)",
        r"start\s+(?:work\s+on\s+)?(.+?)(?:\s*$|\?)",
        r"i\s+want\s+to\s+(?:change|modify|update)\s+(.+?)(?:\s+by|\s+to|\s*$|\?)",
    ],
    "finalize-change": [
        r"finalize\s+(?:change\s+)?(?:for\s+)?(.+?)(?:\s*$|\?)",
        r"complete\s+(?:the\s+)?work\s+(?:on\s+)?(.+?)(?:\s*$|\?)",
        r"finish\s+(?:editing\s+)?(.+?)(?:\s*$|\?)",
    ],
    "list-projects": [
        r"list\s+(?:all\s+)?projects",
        r"what\s+projects\s+are\s+available",
        r"show\s+(?:me\s+)?(?:the\s+)?projects",
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
                project = match.group(1).strip() if match.groups() else None
                # Clean up project name (remove trailing punctuation)
                if project:
                    project = project.rstrip('?.!')
                return intent, project
    
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# Configuration & Resolution
# ─────────────────────────────────────────────────────────────────────────────

def _load_config() -> dict[str, Any]:
    """Load attention-config.json."""
    if not ATTENTION_CONFIG.exists():
        raise FileNotFoundError(f"Missing attention-config.json at {SKILL_ROOT}")
    return json.loads(ATTENTION_CONFIG.read_text(encoding="utf-8"))


def list_projects() -> list[str]:
    """Return list of registered project names."""
    config = _load_config()
    return list(config.get("project_registry", {}).keys())


def resolve_project(project_name: str) -> Path:
    """Resolve project path via config with fuzzy matching."""
    config = _load_config()
    registry = config.get("project_registry", {})
    
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
    registry = config.get("project_registry", {})
    
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
        _user_sessions[user_id] = {"pending_intent": None, "selected_project": None}
    return _user_sessions[user_id]


def clear_session(user_id: str):
    """Clear user session state."""
    _user_sessions.pop(user_id, None)


# ─────────────────────────────────────────────────────────────────────────────
# Persistent Index (State Tracking with Timestamps)
# ─────────────────────────────────────────────────────────────────────────────

ATTENTION_INDEX = SKILL_ROOT / ".attention" / "index.json"
ATTENTION_VERSION = "3.2.4"
STALENESS_DAYS = 7  # Warn if not checked in 7 days


def _load_index() -> dict:
    """Load or create attention index with timestamps."""
    if ATTENTION_INDEX.exists():
        try:
            return json.loads(ATTENTION_INDEX.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            pass
    
    # Create new index
    return {
        "version": ATTENTION_VERSION,
        "created_at": _now_iso(),
        "last_updated": _now_iso(),
        "projects": {}
    }


def _save_index(index: dict):
    """Save index to disk."""
    ATTENTION_INDEX.parent.mkdir(parents=True, exist_ok=True)
    index["last_updated"] = _now_iso()
    ATTENTION_INDEX.write_text(json.dumps(index, indent=2, default=str), encoding="utf-8")


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
    index = _load_index()
    
    if project not in index["projects"]:
        index["projects"][project] = {
            "first_seen": _now_iso(),
            "operations": {}
        }
    
    index["projects"][project]["operations"][operation] = {
        "timestamp": _now_iso(),
        "result": result
    }
    
    _save_index(index)


def get_project_staleness(project: str) -> dict:
    """Get staleness info for a project."""
    index = _load_index()
    proj_data = index.get("projects", {}).get(project, {})
    ops = proj_data.get("operations", {})
    
    staleness = {
        "last_assemble": None,
        "last_freshness": None,
        "days_since_assemble": None,
        "days_since_freshness": None,
        "is_stale": False,
        "warnings": []
    }
    
    if "assemble" in ops:
        staleness["last_assemble"] = ops["assemble"]["timestamp"]
        staleness["days_since_assemble"] = _days_since(ops["assemble"]["timestamp"])
    
    if "freshness" in ops:
        staleness["last_freshness"] = ops["freshness"]["timestamp"]
        staleness["days_since_freshness"] = _days_since(ops["freshness"]["timestamp"])
    
    # Determine staleness
    if staleness["days_since_assemble"] is not None and staleness["days_since_assemble"] > STALENESS_DAYS:
        staleness["is_stale"] = True
        staleness["warnings"].append(f"Not assembled in {staleness['days_since_assemble']:.0f} days")
    
    if staleness["days_since_freshness"] is not None and staleness["days_since_freshness"] > STALENESS_DAYS:
        staleness["is_stale"] = True
        staleness["warnings"].append(f"Freshness not checked in {staleness['days_since_freshness']:.0f} days")
    
    # Check if !MAP.md has been modified since last assemble
    if staleness["last_assemble"]:
        try:
            project_path = resolve_project(project)
            map_path = project_path / "!MAP.md"
            if map_path.exists():
                import os
                mtime = os.path.getmtime(map_path)
                from datetime import datetime, timezone
                map_modified = datetime.fromtimestamp(mtime, tz=timezone.utc)
                assemble_time = _parse_iso(staleness["last_assemble"])
                if map_modified > assemble_time:
                    staleness["is_stale"] = True
                    staleness["warnings"].append("!MAP.md modified since last assemble")
        except Exception:
            pass
    
    return staleness


# ─────────────────────────────────────────────────────────────────────────────
# Index / Menu Builder (Fast - no !MAP.md parsing)
# ─────────────────────────────────────────────────────────────────────────────

def build_project_index() -> list[dict]:
    """Build project index with staleness awareness."""
    config = _load_config()
    registry = config.get("project_registry", {})
    
    projects = []
    for name, data in registry.items():
        project_info = {
            "name": name,
            "path": data.get("canonical_path", "unknown"),
            "has_task": False,
            "entity_count": 0,
        }
        
        # Quick check for CURRENT_TASK.md (lightweight)
        try:
            task_path = Path(data["canonical_path"]) / "CURRENT_TASK.md"
            project_info["has_task"] = task_path.exists()
            if project_info["has_task"]:
                # Quick scan for status line
                content = task_path.read_text(encoding="utf-8")[:500]
                if "COMPLETED" in content[:200]:
                    project_info["task_status"] = "completed"
                elif "IN PROGRESS" in content[:200] or "ACTIVE" in content[:200]:
                    project_info["task_status"] = "active"
                else:
                    project_info["task_status"] = "idle"
        except Exception:
            pass
        
        # Get staleness info from index
        staleness = get_project_staleness(name)
        project_info["staleness"] = staleness
        
        projects.append(project_info)
    
    return projects


def format_index_menu(projects: list[dict], platform: str) -> RouteResponse:
    """Format project index with staleness indicators."""
    index = _load_index()
    
    lines = [f"*Attention Layer v{ATTENTION_VERSION}* — Registered Projects\n"]
    
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
        lines.append("_Run freshness check or assemble to update._")
    else:
        lines.append(f"\n✅ All projects up to date")
        lines.append("_Last index update: " + index.get("last_updated", "unknown")[:10] + "_")
    
    lines.append(f"\n_Select a project to see actions._")
    
    # Build menu items - prioritize stale projects, group into rows of 2
    menu_items = []
    row_num = 0
    
    # First add stale projects
    for p in projects:
        if p.get("staleness", {}).get("is_stale"):
            menu_items.append({
                "label": f"🔴 {p['name']}",
                "action": "show-actions",
                "project": p["name"],
                "row": row_num // 2  # 2 buttons per row
            })
            row_num += 1
    
    # Then add others
    for p in projects:
        if not p.get("staleness", {}).get("is_stale"):
            menu_items.append({
                "label": f"📋 {p['name']}",
                "action": "show-actions",
                "project": p["name"],
                "row": row_num // 2  # 2 buttons per row
            })
            row_num += 1
    
    return RouteResponse(
        text="\n".join(lines),
        suggest_menu=True,
        menu_items=menu_items
    )
    
    return RouteResponse(
        text="\n".join(lines),
        suggest_menu=True,
        menu_items=menu_items
    )


def format_project_actions(project: str, platform: str) -> RouteResponse:
    """Show available actions for a selected project."""
    text = f"*📁 {project}*\n\nWhat do you want to do?"
    
    # Group into rows of 2 for side-by-side buttons (like provider selection)
    menu_items = [
        {"label": "🔍 Assemble", "action": "assemble", "project": project, "row": 0},
        {"label": "✓ Freshness", "action": "freshness", "project": project, "row": 0},
        {"label": "📝 Status", "action": "status", "project": project, "row": 1},
        {"label": "▶️ Declare", "action": "declare", "project": project, "row": 1},
    ]
    
    return RouteResponse(
        text=text,
        suggest_menu=True,
        menu_items=menu_items
    )


def format_main_menu(platform: str) -> RouteResponse:
    """Show main attention-layer operations menu."""
    index = _load_index()
    
    lines = [f"*Attention Layer* — v{ATTENTION_VERSION}\n"]
    lines.append(f"Index updated: {index.get('last_updated', 'unknown')[:10]}")
    lines.append(f"Registered: {len(index.get('projects', {}))} project(s)\n")
    
    # Check for any stale projects
    config = _load_config()
    stale_count = 0
    for name in config.get("project_registry", {}):
        staleness = get_project_staleness(name)
        if staleness.get("is_stale"):
            stale_count += 1
    
    if stale_count > 0:
        lines.append(f"⚠️ *{stale_count} project(s) stale*\n")
    
    lines.append("Select operation:")
    
    menu_items = [
        {"label": "📋 Projects", "action": "list-projects", "project": "", "row": 0},
        {"label": "🔍 Assemble", "action": "menu-assemble", "project": "", "row": 0},
        {"label": "✓ Freshness", "action": "menu-freshness", "project": "", "row": 1},
        {"label": "📝 Status", "action": "menu-status", "project": "", "row": 1},
        {"label": "▶️ Declare", "action": "menu-declare", "project": "", "row": 2},
        {"label": "🏁 Finalize", "action": "menu-finalize", "project": "", "row": 2},
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

    # Check for explicit command prefix (handle both dash and underscore variants)
    # Telegram converts /attention-layer to /attention_layer in bot commands
    if text.startswith(("/attention", "!attention", "/attention_layer", "!attention_layer")):
        # Normalize: replace underscore with dash for consistency
        text = text.replace("attention_layer", "attention")
        remainder = text.split(None, 1)[1] if " " in text else ""
        if not remainder:
            # Bare /attention command - show main menu (not just projects)
            return format_main_menu(request.platform)
        text = remainder

    # Handle menu-based action callbacks (from main menu buttons)
    menu_actions = ("menu-assemble", "menu-freshness", "menu-status", "menu-declare", "menu-finalize")
    if text in menu_actions:
        actual_intent = text.replace("menu-", "")
        session["menu_pending"] = actual_intent
        projects = build_project_index()

        # Show project selector with the action pre-selected
        lines = [f"*{actual_intent.title()}* — Select project:\n"]
        for p in projects:
            status = "🔴" if p.get("staleness", {}).get("is_stale") else "📋"
            lines.append(f"{status} {p['name']}")

        menu_items = []
        row_num = 0
        for p in projects:
            status = "🔴" if p.get("staleness", {}).get("is_stale") else "📋"
            menu_items.append({
                "label": f"{status} {p['name']}",
                "action": actual_intent,
                "project": p["name"],
                "row": row_num // 2
            })
            row_num += 1

        return RouteResponse(
            text="\n".join(lines),
            suggest_menu=True,
            menu_items=menu_items
        )
    
    # Handle callback-style actions (from inline buttons)
    if text.startswith(("show-actions ", "action:")):
        # Extract project name
        if text.startswith("show-actions "):
            project = text[13:].strip()
        else:
            project = text.split(":")[1] if ":" in text else ""
        if project:
            session["selected_project"] = project
            return format_project_actions(project, request.platform)
    
    # Check for pending intent (confirmation flow)
    if session.get("pending_intent"):
        pending = session["pending_intent"]
        
        if text.lower() in ("yes", "y", "confirm", "proceed", "go"):
            # User confirmed - execute the pending action
            session["pending_intent"] = None
            return execute_intent(pending["intent"], pending["project"], request)
        elif text.lower() in ("no", "n", "cancel", "abort"):
            session["pending_intent"] = None
            return RouteResponse(text="Cancelled. Use /attention to see the menu.")
        else:
            # Still waiting for confirmation
            return RouteResponse(
                text=f"Pending: {pending['intent']} for *{pending['project']}*\n\nConfirm? (yes/no)",
                suggest_menu=True,
                menu_items=[
                    {"label": "✓ Yes, proceed", "action": pending["intent"], "project": pending["project"]},
                    {"label": "✗ Cancel", "action": "cancel", "project": ""}
                ]
            )
    
    # Detect intent
    intent, project = detect_intent(text)
    
    if not intent:
        # No clear intent - show index menu (fast, no !MAP.md reads yet)
        projects = build_project_index()
        return format_index_menu(projects, request.platform)
    
    if intent == "list-projects":
        return format_main_menu(request.platform)
    
    # Intents that need a project - but we don't execute yet!
    # Store intent and ask for confirmation first
    if not project:
        return format_main_menu(request.platform)
    
    # Normalize project name
    try:
        canonical_project = normalize_project_name(project)
    except ValueError as e:
        return RouteResponse(text=f"Unknown project: {project}. Use /attention to see registered projects.")
    
    # Store pending intent and ask for confirmation
    session["pending_intent"] = {"intent": intent, "project": canonical_project}
    session["selected_project"] = canonical_project
    
    return RouteResponse(
        text=f"*Intent Declaration*\n\nAction: {intent}\nProject: {canonical_project}\n\nThis will read !MAP.md and perform the operation. Confirm?",
        suggest_menu=True,
        menu_items=[
            {"label": f"✓ Confirm {intent}", "action": intent, "project": canonical_project},
            {"label": "✗ Cancel", "action": "cancel", "project": ""}
        ]
    )


def execute_intent(intent: str, project: str, request: RouteRequest) -> RouteResponse:
    """Execute the intent after confirmation (this is where !MAP.md gets read)."""
    try:
        if intent == "assemble":
            stdout, stderr, rc = run_cli("assemble", project)
            # Record in index after successful operation
            update_project_index(project, "assemble", "ok" if rc == 0 else "fail")
            return RouteResponse(
                text=stdout if rc == 0 else f"Error: {stderr or stdout}",
                structured_data={"command": "assemble", "project": project, "rc": rc}
            )
        
        elif intent == "freshness":
            stdout, stderr, rc = run_cli("map-freshness-check", project)
            update_project_index(project, "freshness", "ok" if rc == 0 else "fail")
            return RouteResponse(
                text=stdout if rc == 0 else f"Error: {stderr or stdout}",
                structured_data={"command": "freshness", "project": project, "rc": rc}
            )
            return RouteResponse(
                text=stdout if rc == 0 else f"Error: {stderr or stdout}",
                structured_data={"command": "freshness", "project": project, "rc": rc}
            )
        
        elif intent == "status":
            project_path = resolve_project(project)
            task_path = project_path / "CURRENT_TASK.md"
            if not task_path.exists():
                return RouteResponse(text=f"No CURRENT_TASK.md for {project}")
            content = task_path.read_text(encoding="utf-8")[:1500]
            return RouteResponse(
                text=f"**{project} - Current Task**\n\n{content}",
                structured_data={"command": "status", "project": project}
            )
        
        elif intent == "declare-intent":
            # Return a form/flow request
            return RouteResponse(
                text=f"Starting declare-intent for **{project}**...\n\nPlease specify:\n- Affected entities (comma-separated)\n- First principle summary\n- Requires new entity? (yes/no)",
                structured_data={
                    "command": "declare-intent",
                    "project": project,
                    "next_step": "collect-details"
                },
                suggest_menu=True,
                menu_items=[
                    {"label": "Continue", "action": "declare-flow", "project": project, "step": "start"},
                    {"label": "Cancel", "action": "cancel"}
                ]
            )
        
        elif intent == "finalize-change":
            stdout, stderr, rc = run_cli("map-freshness-check", project)  # First check freshness
            if rc != 0:
                return RouteResponse(
                    text=f"Cannot finalize - freshness check failed:\n{stderr or stdout}",
                    structured_data={"blocked": True, "reason": "freshness-failed"}
                )
            return RouteResponse(
                text=f"Ready to finalize **{project}**. Run:\n`attention finalize-change {project}`",
                structured_data={"command": "finalize-ready", "project": project}
            )
        
        elif intent == "cancel":
            return RouteResponse(text="Cancelled. Use /attention to see the menu.")
        
        else:
            return RouteResponse(text=f"Intent '{intent}' not yet implemented")
            
    except Exception as e:
        return RouteResponse(text=f"Error executing {intent}: {e}")
    
    if intent == "list-projects":
        projects = list_projects()
        return RouteResponse(
            text=f"Registered projects ({len(projects)}):\n" + "\n".join(f"• {p}" for p in projects),
            structured_data={"projects": projects}
        )
    
    # Intents that need a project
    if not project:
        return RouteResponse(
            text=f"You want to {intent}, but which project?\nAvailable: {', '.join(list_projects())}",
            suggest_menu=True
        )
    
    # Execute the intent
    try:
        if intent == "assemble":
            stdout, stderr, rc = run_cli("assemble", project)
            return RouteResponse(
                text=stdout if rc == 0 else f"Error: {stderr or stdout}",
                structured_data={"command": "assemble", "project": project, "rc": rc}
            )
        
        elif intent == "freshness":
            stdout, stderr, rc = run_cli("map-freshness-check", project)
            return RouteResponse(
                text=stdout if rc == 0 else f"Error: {stderr or stdout}",
                structured_data={"command": "freshness", "project": project, "rc": rc}
            )
        
        elif intent == "status":
            project_path = resolve_project(project)
            task_path = project_path / "CURRENT_TASK.md"
            if not task_path.exists():
                return RouteResponse(text=f"No CURRENT_TASK.md for {project}")
            content = task_path.read_text(encoding="utf-8")[:1500]
            return RouteResponse(
                text=f"**{project} - Current Task**\n\n{content}",
                structured_data={"command": "status", "project": project}
            )
        
        elif intent == "declare-intent":
            # Return a form/flow request
            return RouteResponse(
                text=f"Starting declare-intent for **{project}**...",
                structured_data={
                    "command": "declare-intent",
                    "project": project,
                    "next_step": "select-entities"
                },
                suggest_menu=True,
                menu_items=[
                    {"label": "Continue", "action": "declare-flow", "project": project, "step": "start"},
                    {"label": "Cancel", "action": "cancel"}
                ]
            )
        
        elif intent == "finalize-change":
            stdout, stderr, rc = run_cli("map-freshness-check", project)  # First check freshness
            if rc != 0:
                return RouteResponse(
                    text=f"Cannot finalize - freshness check failed:\n{stderr or stdout}",
                    structured_data={"blocked": True, "reason": "freshness-failed"}
                )
            return RouteResponse(
                text=f"Ready to finalize **{project}**. Run:\n`attention finalize-change {project}`",
                structured_data={"command": "finalize-ready", "project": project}
            )
        
        else:
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
        print("  python3 service_router.py tui 'declare intent for attention-layer'")
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
