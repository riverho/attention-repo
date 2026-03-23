#!/usr/bin/env python3
"""Attention engine: first-principles + CI/CD entity mapping gate."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add scripts dir to path for resolver
_SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPT_DIR))

try:
    from resolve import (
        build_default_config,
        central_config_exists,
        detect_project_candidates,
        ensure_index,
        get_config_path,
        get_entity_resolution_path,
        get_index_path,
        get_skill_runtime,
        get_update_gate_status,
        LEGACY_CONFIG_PATH,
        load_index,
        load_config,
        record_project_operation,
        register_project,
        reindex_registered_projects,
        resolve_project_name_from_path,
        save_index,
        resolve_project_path,
        save_config,
        summarize_current_task,
    )
    from version_info import get_version
except ImportError as _e:
    resolve_project_path = None
    load_config = None
    get_entity_resolution_path = None
    build_default_config = None
    central_config_exists = None
    detect_project_candidates = None
    ensure_index = None
    get_config_path = None
    get_index_path = None
    get_skill_runtime = None
    get_update_gate_status = None
    record_project_operation = None
    register_project = None
    reindex_registered_projects = None
    resolve_project_name_from_path = None
    save_index = None
    save_config = None
    summarize_current_task = None
    LEGACY_CONFIG_PATH = None
    load_index = None
    from scripts.version_info import get_version

ENTITY_START = "<!-- ENTITY_REGISTRY_START -->"
ENTITY_END = "<!-- ENTITY_REGISTRY_END -->"
ATTN_DIR = ".attention"
DECLARATION_FILE = "architectural_intent.json"
ATTENTION_VERSION = get_version()
SKILL_REPO = _SCRIPT_DIR.parent


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def replace_markdown_section(text: str, heading: str, body: str) -> str:
    section = f"## {heading}\n{body.strip()}\n"
    pattern = re.compile(rf"## {re.escape(heading)}\n.*?(?=\n## |\Z)", re.DOTALL)
    if pattern.search(text):
        return pattern.sub(section, text).rstrip() + "\n"
    base = text.rstrip()
    if base:
        base += "\n\n"
    return base + section


def run_git(repo: Path, *args: str) -> str:
    try:
        out = subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.STDOUT)
        return out.decode("utf-8").strip()
    except subprocess.CalledProcessError as exc:
        return f"<git command failed: {' '.join(args)}>\n{exc.output.decode('utf-8', errors='replace').strip()}"


def resolve_repo(repo_arg: str) -> Path:
    """Resolve repo argument: project name via config, or direct path."""
    # First try as path
    path = Path(repo_arg).expanduser()
    if path.exists():
        return path.resolve()

    # Try as registered project name
    if resolve_project_path is not None:
        try:
            return resolve_project_path(repo_arg)
        except (ValueError, RuntimeError, FileNotFoundError):
            pass  # Fall through to error

    # Neither worked
    registered = "resolver unavailable"
    if resolve_project_path is not None:
        try:
            from resolve import list_registered_projects
            registered = list_registered_projects()
        except Exception:
            pass

    raise ValueError(
        f"Cannot resolve: {repo_arg}\n"
        f"Not a valid path, and not a registered project.\n"
        f"Registered projects: {registered}"
    )


def parse_bool(raw: str) -> bool:
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "y"}:
        return True
    if value in {"0", "false", "no", "n"}:
        return False
    raise ValueError(f"Invalid boolean value: {raw}")


def split_entities(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def extract_entity_registry(map_text: str) -> dict[str, Any]:
    pattern = re.compile(re.escape(ENTITY_START) + r"\n(.*?)\n" + re.escape(ENTITY_END), re.DOTALL)
    match = pattern.search(map_text)
    if not match:
        raise ValueError("Missing entity registry block in !MAP.md")
    payload = match.group(1).strip()
    data = json.loads(payload)
    if not isinstance(data, dict) or "entities" not in data:
        raise ValueError("Entity registry must be a JSON object with an 'entities' array")
    if not isinstance(data["entities"], list):
        raise ValueError("Entity registry field 'entities' must be an array")
    return data


def write_entity_registry(map_path: Path, registry: dict[str, Any]) -> None:
    map_text = read_text(map_path)
    rendered = json.dumps(registry, indent=2)
    block = f"{ENTITY_START}\n{rendered}\n{ENTITY_END}"

    if ENTITY_START in map_text and ENTITY_END in map_text:
        pattern = re.compile(re.escape(ENTITY_START) + r"\n.*?\n" + re.escape(ENTITY_END), re.DOTALL)
        next_text = pattern.sub(block, map_text)
    else:
        next_text = map_text.rstrip() + "\n\n## Entity Registry\n" + block + "\n"

    write_text(map_path, next_text)


def default_map_template() -> str:
    return """# !MAP.md

## Purpose
Document the repository purpose and operational boundaries here.

## Runbook
- Build: `...`
- Test: `...`
- Lint: `...`

## Architecture Boundaries
- Boundary 1: ...
- Boundary 2: ...

## Non-Goals
- ...

## Entity Registry
<!-- ENTITY_REGISTRY_START -->
{
  "entities": []
}
<!-- ENTITY_REGISTRY_END -->
"""


def default_task_template() -> str:
    return """# CURRENT_TASK.md

## Goal
Describe the current task.

## Constraints
- Keep changes minimal
- Preserve existing behavior

## Done When
- [ ] Tests pass
- [ ] Changes committed
"""


def recovered_task_template(recovered_excerpt: str) -> str:
    base = """# CURRENT_TASK.md

## Status
Recovered task memory requires review before work resumes.

## Recovery Notes
- Templates were rebuilt by `reinit`.
- Review and rewrite this file before resuming normal work.
"""
    if recovered_excerpt:
        base += f"\n## Recovered Context\n{recovered_excerpt.strip()}\n"
    return base


def is_map_valid(text: str) -> bool:
    if not text.strip() or "# !MAP.md" not in text:
        return False
    try:
        extract_entity_registry(text)
    except Exception:
        return False
    return True


def is_task_valid(text: str) -> bool:
    if not text.strip():
        return False
    normalized = re.sub(r"^<!-- Last synced:.*?-->\n", "", text.strip())
    return normalized.startswith("# CURRENT_TASK.md")


def extract_recovered_excerpt(text: str, *, max_chars: int = 1200) -> str:
    cleaned = re.sub(r"^<!-- Last synced:.*?-->\n", "", text.strip())
    if not cleaned:
        return ""
    lines: list[str] = []
    for raw_line in cleaned.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        lines.append(line)
    excerpt = "\n".join(lines).strip()
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars].rstrip() + "..."
    return excerpt


def _repair_local_memory(repo: Path) -> list[str]:
    map_path = repo / "!MAP.md"
    task_path = repo / "CURRENT_TASK.md"
    recovery_root = repo / ATTN_DIR / "recovery" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    repaired: list[str] = []

    map_text = read_text(map_path)
    task_text = read_text(task_path)
    map_valid = is_map_valid(map_text)
    task_valid = is_task_valid(task_text)

    if map_valid and task_valid:
        return repaired

    recovery_root.mkdir(parents=True, exist_ok=True)
    for path in (
        map_path,
        task_path,
        repo / ATTN_DIR / "map_freshness.json",
        repo / ATTN_DIR / "ATTENTION_FINALIZE.md",
    ):
        if not path.exists():
            continue
        target = recovery_root / path.relative_to(repo)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)

    if not map_valid:
        write_text(map_path, default_map_template())
        repaired.append("!MAP.md")

    if not task_valid:
        recovered_excerpt = extract_recovered_excerpt(task_text)
        next_task = recovered_task_template(recovered_excerpt) if recovered_excerpt else default_task_template()
        write_text(task_path, next_task)
        repaired.append("CURRENT_TASK.md")

    for stale_path in (repo / ATTN_DIR / "map_freshness.json", repo / ATTN_DIR / "ATTENTION_FINALIZE.md"):
        if stale_path.exists():
            stale_path.unlink()

    return repaired


def ensure_templates(repo: Path) -> None:
    map_path = repo / "!MAP.md"
    task_path = repo / "CURRENT_TASK.md"

    if not map_path.exists():
        write_text(map_path, default_map_template())

    if not task_path.exists():
        write_text(task_path, default_task_template())


def resolved_project_name(repo: Path) -> str:
    if resolve_project_name_from_path is not None:
        try:
            resolved = resolve_project_name_from_path(repo)
            if resolved:
                return resolved
        except Exception:
            pass
    return repo.name


def declaration_path(repo: Path) -> Path:
    return repo / ATTN_DIR / DECLARATION_FILE


def load_declaration(repo: Path) -> dict[str, Any]:
    path = declaration_path(repo)
    if not path.exists():
        raise ValueError("Missing declaration. Run declare-intent first.")
    return json.loads(path.read_text(encoding="utf-8"))


def get_entity_map(repo: Path) -> dict[str, dict[str, Any]]:
    map_path = repo / "!MAP.md"
    map_text = read_text(map_path)
    registry = extract_entity_registry(map_text)
    entities = registry.get("entities", [])
    return {str(e.get("id")): e for e in entities if isinstance(e, dict) and e.get("id")}


def validate_declaration(
    repo: Path,
    affected_entities: list[str],
    deployment_pipeline: str,
    summary: str,
    requires_new_entity: bool,
    task_type: str,
) -> None:
    words = [w for w in summary.strip().split() if w]
    if len(words) < 6:
        raise ValueError("first_principle_summary must contain at least 6 words")

    entity_map = get_entity_map(repo)
    missing = [eid for eid in affected_entities if eid not in entity_map]
    if missing and not requires_new_entity:
        raise ValueError(f"Unknown entity IDs: {', '.join(missing)}")

    docs_like = task_type in {"docs", "tests"}
    if not docs_like and not requires_new_entity and not affected_entities:
        raise ValueError("affected_entities cannot be empty unless requires_new_entity=true")

    if docs_like:
        if deployment_pipeline != "N/A":
            pipe_file = repo / deployment_pipeline
            if not pipe_file.exists():
                raise ValueError(f"deployment_pipeline does not exist: {deployment_pipeline}")
    else:
        pipe_file = repo / deployment_pipeline
        if not pipe_file.exists():
            raise ValueError(f"deployment_pipeline does not exist: {deployment_pipeline}")

    if affected_entities:
        mapped = {entity_map[eid].get("ci_cd") for eid in affected_entities if eid in entity_map}
        mapped.discard(None)
        mapped.discard("")
        if mapped and (len(mapped) > 1 or deployment_pipeline not in mapped):
            allowed = ", ".join(sorted(str(x) for x in mapped))
            raise ValueError(
                "deployment_pipeline must match the selected entity mappings. "
                f"Expected one of: {allowed}"
            )


def cmd_declare_intent(args: argparse.Namespace) -> None:
    repo = resolve_repo(args.repo)
    affected_entities = split_entities(args.affected_entities)
    requires_new_entity = parse_bool(args.requires_new_entity)

    validate_declaration(
        repo,
        affected_entities,
        args.deployment_pipeline,
        args.first_principle_summary,
        requires_new_entity,
        args.task_type,
    )

    payload = {
        "declared_at": utc_now(),
        "task_type": args.task_type,
        "affected_entities": affected_entities,
        "deployment_pipeline": args.deployment_pipeline,
        "first_principle_summary": args.first_principle_summary.strip(),
        "requires_new_entity": requires_new_entity,
    }

    out = declaration_path(repo)
    write_text(out, json.dumps(payload, indent=2) + "\n")
    if record_project_operation is not None:
        record_project_operation(
            resolved_project_name(repo),
            repo,
            "declare-intent",
            extra={"status": "active"},
        )
    print(f"Declared architectural intent: {out}")


def summarize_file(path: Path, max_lines: int = 180, max_chars: int = 12000) -> str:
    if not path.exists():
        return f"[{path}]\n<missing>"
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    clipped = lines[:max_lines]
    body = "\n".join(clipped)
    if len(body) > max_chars:
        body = body[:max_chars]
    suffix = ""
    if len(lines) > max_lines:
        suffix = f"\n... <truncated: {len(lines) - max_lines} more lines>"
    return f"[{path}]\n{body}{suffix}"


def build_injected_context(repo: Path, declaration: dict[str, Any]) -> str:
    entity_map = get_entity_map(repo)

    paths: list[Path] = []

    for entity_id in declaration.get("affected_entities", []):
        entity = entity_map.get(entity_id)
        if not entity:
            continue
        ci_cd = entity.get("ci_cd")
        if isinstance(ci_cd, str) and ci_cd.strip():
            paths.append(repo / ci_cd)

    declared_pipeline = declaration.get("deployment_pipeline")
    if isinstance(declared_pipeline, str) and declared_pipeline != "N/A":
        paths.append(repo / declared_pipeline)

    for runtime in ["wrangler.toml", "package.json", "tsconfig.json"]:
        runtime_path = repo / runtime
        if runtime_path.exists():
            paths.append(runtime_path)

    unique_paths: list[Path] = []
    seen: set[str] = set()
    for p in paths:
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        unique_paths.append(p)

    if not unique_paths:
        return "<no CI/CD or runtime files injected>"

    return "\n\n".join(summarize_file(p) for p in unique_paths)


def cmd_assemble(args: argparse.Namespace) -> None:
    repo = resolve_repo(args.repo)
    declaration = load_declaration(repo)

    map_text = read_text(repo / "!MAP.md").strip() or "<missing !MAP.md>"
    task_text = read_text(repo / "CURRENT_TASK.md").strip() or "<empty CURRENT_TASK.md>"

    git_status = run_git(repo, "status", "-s") or "<clean>"
    recent_commit = run_git(repo, "log", "-1", "--stat")
    injected = build_injected_context(repo, declaration)

    payload = (
        "[SYSTEM PROMPT]\n"
        "You are a Staff Infrastructure Engineer.\n"
        "Operate on first principles and CI/CD entity mapping.\n"
        "Before any code modification, you must produce architectural mapping and avoid creating new architecture when an existing entity can be extended.\n"
        "No write/edit actions are allowed unless declare_architectural_intent succeeded.\n\n"
        "[ARCHITECTURE]\n"
        f"{map_text}\n\n"
        "[DECLARED ARCHITECTURAL INTENT]\n"
        f"{json.dumps(declaration, indent=2)}\n\n"
        "[CURRENT STATE]\n"
        f"Git status:\n{git_status}\n\n"
        f"Recent changes:\n{recent_commit}\n\n"
        "[CURRENT TASK]\n"
        f"{task_text}\n\n"
        "[INJECTED CI/CD + RUNTIME CONTEXT]\n"
        f"{injected}\n\n"
        "[YOUR TOOLS]\n"
        "- ripgrep_search\n"
        "- read_file\n"
        "- edit_file\n"
        "- run_tests\n"
        "- update_current_task\n"
        "- register_new_entity\n"
        "- finalize_change\n"
    )

    if record_project_operation is not None:
        record_project_operation(resolved_project_name(repo), repo, "assemble")
    print(payload)


def cmd_update_task(args: argparse.Namespace) -> None:
    repo = resolve_repo(args.repo)
    status = args.status_markdown.strip()
    if not status:
        raise ValueError("status_markdown cannot be empty")

    declaration = load_declaration(repo)
    text = (
        "# CURRENT_TASK.md\n\n"
        "## Status\n"
        f"{status}\n\n"
        "## Architectural Intent\n"
        f"- Entities: {', '.join(declaration.get('affected_entities', [])) or 'None'}\n"
        f"- Pipeline: {declaration.get('deployment_pipeline')}\n"
        f"- First Principle: {declaration.get('first_principle_summary')}\n"
        f"- Requires New Entity: {declaration.get('requires_new_entity')}\n\n"
        f"## Updated\n{utc_now()}\n"
    )
    write_text(repo / "CURRENT_TASK.md", text)
    if record_project_operation is not None:
        record_project_operation(
            resolved_project_name(repo),
            repo,
            "update-task",
            extra={"status": "active"},
        )
    print(f"Updated: {repo / 'CURRENT_TASK.md'}")


def cmd_register_new_entity(args: argparse.Namespace) -> None:
    repo = resolve_repo(args.repo)
    declaration = load_declaration(repo)
    if not declaration.get("requires_new_entity"):
        raise ValueError("register-new-entity is only allowed when requires_new_entity=true")

    map_path = repo / "!MAP.md"
    registry = extract_entity_registry(read_text(map_path))
    entities = registry.get("entities", [])

    existing_ids = {str(e.get("id")) for e in entities if isinstance(e, dict)}
    if args.id in existing_ids:
        raise ValueError(f"Entity ID already exists: {args.id}")

    pipeline_path = repo / args.ci_cd
    if not pipeline_path.exists():
        raise ValueError(f"ci_cd pipeline does not exist: {args.ci_cd}")

    new_entity = {
        "id": args.id,
        "type": args.type,
        "file_path": args.file_path,
        "ci_cd": args.ci_cd,
        "endpoint": args.endpoint,
        "description": args.description,
    }
    entities.append(new_entity)
    registry["entities"] = entities
    write_entity_registry(map_path, registry)
    print(f"Registered new entity in {map_path}: {args.id}")


def cmd_map_freshness_check(args: argparse.Namespace) -> None:
    """Verify !MAP.md entity metadata matches actual implementation."""
    repo = resolve_repo(args.repo)
    declaration = load_declaration(repo)
    entity_map = get_entity_map(repo)

    affected = declaration.get("affected_entities", [])
    issues = []
    verified = []

    for eid in affected:
        entity = entity_map.get(eid)
        if not entity:
            issues.append(f"Entity {eid}: not found in !MAP.md")
            continue

        # Check file_path exists
        fp = entity.get("file_path")
        if fp:
            full_path = repo / fp
            if not full_path.exists():
                issues.append(f"Entity {eid}: file_path '{fp}' does not exist")
            else:
                verified.append(f"Entity {eid}: file_path '{fp}' exists")

        # Check ci_cd pipeline exists
        cicd = entity.get("ci_cd")
        if cicd:
            cicd_path = repo / cicd
            if not cicd_path.exists():
                issues.append(f"Entity {eid}: ci_cd '{cicd}' does not exist")
            else:
                verified.append(f"Entity {eid}: ci_cd '{cicd}' exists")

    # Load or create freshness record
    freshness_path = repo / ATTN_DIR / "map_freshness.json"
    record = {"checked_at": utc_now(), "affected_entities": affected, "issues": issues, "verified": verified}

    if args.no_change_justification:
        record["no_change_justification"] = args.no_change_justification
    elif issues:
        record["status"] = "BLOCKED"
        write_text(freshness_path, json.dumps(record, indent=2) + "\n")
        print(f"Map freshness check BLOCKED: {len(issues)} issues found")
        for i in issues:
            print(f"  - {i}")
        raise SystemExit(1)
    else:
        record["status"] = "PASS"

    write_text(freshness_path, json.dumps(record, indent=2) + "\n")
    if record_project_operation is not None:
        record_project_operation(resolved_project_name(repo), repo, "freshness")
    print(f"Map freshness check PASSED: {len(verified)} items verified")
    for v in verified:
        print(f"  - {v}")

    if args.no_change_justification:
        print(f"No-change justification: {args.no_change_justification}")


def cmd_finalize_change(args: argparse.Namespace) -> None:
    repo = resolve_repo(args.repo)
    declaration = load_declaration(repo)

    # Enforce map-freshness-check ran
    freshness_path = repo / ATTN_DIR / "map_freshness.json"
    if not freshness_path.exists():
        print("ERROR: Map freshness check not performed.")
        print("Run: attention map-freshness-check <repo> [--no-change-justification '...']")
        raise SystemExit(1)

    freshness = json.loads(freshness_path.read_text(encoding="utf-8"))
    if freshness.get("status") != "PASS" and not freshness.get("no_change_justification"):
        print("ERROR: Map freshness check did not pass.")
        print(f"Issues: {freshness.get('issues', [])}")
        raise SystemExit(1)

    changed = run_git(repo, "status", "-s")
    short_head = run_git(repo, "rev-parse", "--short", "HEAD")

    report = (
        "# ATTENTION_FINALIZE.md\n\n"
        f"## Timestamp\n{utc_now()}\n\n"
        "## Architectural Mapping\n"
        f"- Entities: {', '.join(declaration.get('affected_entities', [])) or 'None'}\n"
        f"- Pipeline: {declaration.get('deployment_pipeline')}\n"
        f"- First Principle: {declaration.get('first_principle_summary')}\n"
        f"- Requires New Entity: {declaration.get('requires_new_entity')}\n\n"
        "## Map Freshness\n"
        f"- Status: {freshness.get('status')}\n"
        f"- Checked At: {freshness.get('checked_at')}\n"
        f"- Verified: {len(freshness.get('verified', []))} items\n"
    )
    if freshness.get("no_change_justification"):
        report += f"- No-Change Justification: {freshness.get('no_change_justification')}\n"
    report += (
        f"- Issues: {len(freshness.get('issues', []))}\n\n"
        "## Validation\n"
        f"- Tests Command: {args.tests_command}\n"
        f"- Tests Result: {args.tests_result}\n"
        f"- Notes: {args.notes}\n\n"
        "## Git\n"
        f"- HEAD: {short_head}\n"
        f"- Working tree:\n{changed or '<clean>'}\n"
    )

    out = repo / ATTN_DIR / "ATTENTION_FINALIZE.md"
    write_text(out, report)
    if record_project_operation is not None:
        record_project_operation(
            resolved_project_name(repo),
            repo,
            "finalize-change",
            extra={"status": "completed"},
        )
    print(f"Wrote finalize report: {out}")


def cmd_clear_task(args: argparse.Namespace) -> None:
    repo = resolve_repo(args.repo)
    write_text(repo / "CURRENT_TASK.md", "# CURRENT_TASK.md\n\n")
    if record_project_operation is not None:
        record_project_operation(
            resolved_project_name(repo),
            repo,
            "clear-task",
            extra={"status": "idle", "task_summary": ""},
        )
    print(f"Cleared: {repo / 'CURRENT_TASK.md'}")


def cmd_release_attention(args: argparse.Namespace) -> None:
    repo = resolve_repo(args.repo)
    task_path = repo / "CURRENT_TASK.md"
    task_text = read_text(task_path).strip()
    if not task_text:
        task_text = "# CURRENT_TASK.md\n"

    now = utc_now()
    note = args.note.strip() or "Released attention."
    attention_body = (
        f"- State: Released\n"
        f"- Released At: {now}\n"
        f"- Note: {note}"
    )
    next_text = replace_markdown_section(task_text + "\n", "Attention State", attention_body)
    write_text(task_path, next_text)
    if record_project_operation is not None:
        record_project_operation(
            resolved_project_name(repo),
            repo,
            "release-attention",
            extra={"status": "released"},
        )
    print(f"Released attention: {task_path}")


def cmd_reinit(args: argparse.Namespace) -> None:
    repo = resolve_repo(args.repo)
    map_path = repo / "!MAP.md"
    task_path = repo / "CURRENT_TASK.md"
    recovery_root = repo / ATTN_DIR / "recovery" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    recovery_root.mkdir(parents=True, exist_ok=True)

    archived: list[str] = []
    for path in (
        map_path,
        task_path,
        declaration_path(repo),
        repo / ATTN_DIR / "map_freshness.json",
        repo / ATTN_DIR / "ATTENTION_FINALIZE.md",
    ):
        if not path.exists():
            continue
        target = recovery_root / path.relative_to(repo)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        archived.append(str(path.relative_to(repo)))

    map_text = read_text(map_path)
    task_text = read_text(task_path)
    map_was_valid = is_map_valid(map_text)
    task_was_valid = is_task_valid(task_text)
    recovered_excerpt = extract_recovered_excerpt(task_text) if args.salvage_task else ""

    if not map_was_valid:
        write_text(map_path, default_map_template())
    elif not map_path.exists():
        write_text(map_path, default_map_template())

    if not task_was_valid:
        write_text(task_path, recovered_task_template(recovered_excerpt))
    elif not task_path.exists():
        write_text(task_path, recovered_task_template(recovered_excerpt))

    for stale_path in (
        repo / ATTN_DIR / "map_freshness.json",
        repo / ATTN_DIR / "ATTENTION_FINALIZE.md",
    ):
        if stale_path.exists():
            stale_path.unlink()

    if record_project_operation is not None:
        record_project_operation(
            resolved_project_name(repo),
            repo,
            "reinit",
            extra={"status": "recovered"},
        )

    print(f"Recovery archive: {recovery_root}")
    if archived:
        print("Archived:")
        for item in archived:
            print(f"  - {item}")
    print(f"!MAP.md: {'kept' if map_was_valid else 'rebuilt'}")
    print(f"CURRENT_TASK.md: {'kept' if task_was_valid else 'rebuilt'}")

    if not args.auto_assemble:
        print("Auto-assemble: skipped")
        return

    try:
        declaration = load_declaration(repo)
        validate_declaration(
            repo,
            declaration.get("affected_entities", []),
            declaration.get("deployment_pipeline", ""),
            declaration.get("first_principle_summary", ""),
            bool(declaration.get("requires_new_entity")),
            declaration.get("task_type", "code"),
        )
    except Exception as exc:
        print(f"Auto-assemble: skipped ({exc})")
        print("Next step: re-declare intent, then run `attention assemble <repo>`.")
        return

    print("Auto-assemble: running")
    cmd_assemble(argparse.Namespace(repo=str(repo)))


def cmd_sync_state(args: argparse.Namespace) -> None:
    """Sync !MAP.md, CURRENT_TASK.md, and index with timestamps and version."""
    repo = resolve_repo(args.repo)
    now = utc_now()
    version = args.version or ATTENTION_VERSION
    description = args.description or "Synced state"
    
    # 1. Update !MAP.md with operational snapshot
    map_path = repo / "!MAP.md"
    map_text = read_text(map_path)
    
    # Add or update Operational Snapshot section
    snapshot_section = f"""## Operational Snapshot
- **Version:** {version}
- **Last Sync:** {now}
- **Description:** {description}
- **Status:** Operational
"""
    
    if "## Operational Snapshot" in map_text:
        # Replace existing section
        map_text = re.sub(
            r"## Operational Snapshot.*?(?=\n## |\Z)",
            snapshot_section.strip() + "\n",
            map_text,
            flags=re.DOTALL
        )
    else:
        # Add before Entity Registry
        map_text = map_text.replace("## Entity Registry", snapshot_section + "\n## Entity Registry")
    
    write_text(map_path, map_text)
    print(f"Updated: {map_path}")
    
    # 2. Update CURRENT_TASK.md with timestamp
    task_path = repo / "CURRENT_TASK.md"
    task_text = read_text(task_path)
    
    # Add sync marker at top
    sync_line = f"<!-- Last synced: {now} | Version: {version} -->\n"
    if task_text.startswith("<!-- Last synced:"):
        # Replace existing sync line
        task_text = re.sub(r"<!-- Last synced:.*?-->\n", sync_line, task_text)
    else:
        task_text = sync_line + task_text
    
    write_text(task_path, task_text)
    print(f"Updated: {task_path}")
    
    # 3. Update index.json
    index_path = repo / ATTN_DIR / "index.json"
    index = {}
    if index_path.exists():
        try:
            index = json.loads(read_text(index_path))
        except json.JSONDecodeError:
            pass
    
    index["version"] = version
    index["last_synced"] = now
    index["last_updated"] = now
    
    # Record sync operation
    if "sync_history" not in index:
        index["sync_history"] = []
    index["sync_history"].append({
        "timestamp": now,
        "version": version,
        "description": description
    })
    # Keep only last 10 syncs
    index["sync_history"] = index["sync_history"][-10:]
    
    write_text(index_path, json.dumps(index, indent=2, default=str))
    print(f"Updated: {index_path}")
    if record_project_operation is not None:
        record_project_operation(
            resolved_project_name(repo),
            repo,
            "sync-state",
            extra={"status": "idle"},
        )
    
    print(f"\n✅ Sync complete: v{version} at {now}")


def _format_candidate_report(candidates: list[dict[str, Any]], title: str) -> str:
    counts = Counter(candidate["classification"] for candidate in candidates)
    lines = [title]
    lines.append(f"Candidates: {len(candidates)}")
    for key in ("ready", "partial", "uninitialized"):
        lines.append(f"- {key}: {counts.get(key, 0)}")
    if not candidates:
        return "\n".join(lines)
    lines.append("")
    for candidate in candidates:
        markers = ",".join(candidate["markers"])
        lines.append(
            f"- {candidate['name']} [{candidate['scope']}] "
            f"{candidate['classification']} registered={candidate['registered']} markers={markers}"
        )
    return "\n".join(lines)


def cmd_init_config(args: argparse.Namespace) -> None:
    if build_default_config is None or save_config is None or get_config_path is None:
        raise RuntimeError("Central config helpers are unavailable.")
    path = get_config_path()
    if path.exists() and not args.force:
        raise ValueError(f"Config already exists: {path}. Use --force to overwrite.")
    config = build_default_config()
    migrated_count = 0
    if LEGACY_CONFIG_PATH is not None and LEGACY_CONFIG_PATH.exists():
        legacy = load_config()
        legacy_projects = legacy.get("projects", {})
        if isinstance(legacy_projects, dict) and legacy_projects:
            config["projects"] = dict(legacy_projects)
            migrated_count = len(legacy_projects)
    save_config(config, path)
    if get_index_path is not None:
        get_index_path().parent.mkdir(parents=True, exist_ok=True)
    print(f"Initialized config: {path}")
    if migrated_count:
        print(f"Migrated {migrated_count} legacy project(s) from {LEGACY_CONFIG_PATH}")


def _ensure_control_plane(create_if_missing: bool = True) -> dict[str, Any]:
    if build_default_config is None or save_config is None:
        raise RuntimeError("Central config helpers are unavailable.")
    if central_config_exists is not None and central_config_exists():
        return load_config()
    if not create_if_missing:
        return build_default_config()
    config = build_default_config()
    save_config(config)
    return config


def cmd_init_workspace(args: argparse.Namespace) -> None:
    if detect_project_candidates is None or register_project is None or reindex_registered_projects is None:
        raise RuntimeError("Workspace init helpers are unavailable.")
    config = _ensure_control_plane(create_if_missing=not args.dry_run)
    candidates = detect_project_candidates(
        config,
        include_skills=args.include_skills,
        include_plugins=args.include_plugins,
    )
    if args.dry_run:
        print(_format_candidate_report(candidates, "Attention-repo init dry run"))
        if get_config_path is not None:
            print(f"\nConfig path: {get_config_path()}")
        if get_index_path is not None:
            print(f"Index path: {get_index_path()}")
        return

    for candidate in candidates:
        register_project(
            config,
            candidate["name"],
            candidate["canonical_path"],
            source=candidate["scope"],
            managed=True,
            scope=candidate["scope"],
        )
        ensure_templates(Path(candidate["canonical_path"]))

    config_path = save_config(config)
    index_path = reindex_registered_projects(config)
    print(_format_candidate_report(candidates, "Attention-repo init complete"))
    print(f"\nUpdated config: {config_path}")
    print(f"Updated index: {index_path}")


def cmd_repair(args: argparse.Namespace) -> None:
    config = load_config()
    repaired = []
    for name, entry in config.get("projects", {}).items():
        repo = resolve_project_path(name, config)
        before_map = (repo / "!MAP.md").exists()
        before_task = (repo / "CURRENT_TASK.md").exists()
        ensure_templates(repo)
        after_map = (repo / "!MAP.md").exists()
        after_task = (repo / "CURRENT_TASK.md").exists()
        if (not before_map and after_map) or (not before_task and after_task):
            repaired.append(name)
        if record_project_operation is not None:
            record_project_operation(name, repo, "repair")
    index_path = reindex_registered_projects(config)
    print(f"Repair complete. Projects touched: {len(repaired)}")
    for name in repaired:
        print(f"- {name}")
    print(f"Updated index: {index_path}")


def cmd_reindex(args: argparse.Namespace) -> None:
    config = load_config()
    index_path = reindex_registered_projects(config)
    print(f"Reindexed {len(config.get('projects', {}))} project(s): {index_path}")


def cmd_bootstrap_update(args: argparse.Namespace) -> None:
    if (
        build_default_config is None
        or save_config is None
        or ensure_index is None
        or load_index is None
        or save_index is None
        or get_update_gate_status is None
        or summarize_current_task is None
    ):
        raise RuntimeError("Update bootstrap helpers are unavailable.")

    config_created = False
    if central_config_exists is None or not central_config_exists():
        config = build_default_config()
        save_config(config)
        config_created = True
    else:
        config = load_config()

    repaired = _repair_local_memory(SKILL_REPO)

    if reindex_registered_projects is not None:
        reindex_registered_projects(config)
    ensure_index()
    index = load_index()

    task_status, task_summary = summarize_current_task(SKILL_REPO)
    index["skill_runtime"] = {
        "compiled_version": ATTENTION_VERSION,
        "compiled_at": utc_now(),
        "skill_path": str(SKILL_REPO),
        "map_path": str(SKILL_REPO / "!MAP.md"),
        "task_path": str(SKILL_REPO / "CURRENT_TASK.md"),
        "map_valid": is_map_valid(read_text(SKILL_REPO / "!MAP.md")),
        "task_valid": is_task_valid(read_text(SKILL_REPO / "CURRENT_TASK.md")),
        "task_status": task_status,
        "task_summary": task_summary,
    }
    index["version"] = ATTENTION_VERSION
    save_index(index)

    gate = get_update_gate_status(ATTENTION_VERSION, index=index)

    print(f"Bootstrapped attention-repo control plane for v{ATTENTION_VERSION}")
    if config_created and get_config_path is not None:
        print(f"Created config: {get_config_path()}")
    if get_index_path is not None:
        print(f"Updated index: {get_index_path()}")
    print(f"Skill path: {SKILL_REPO}")
    if repaired:
        print("Repaired local memory:")
        for item in repaired:
            print(f"- {item}")
    else:
        print("Local memory: already valid")
    print(f"Task status: {task_status or 'unknown'}")
    print(f"Task summary: {task_summary or '<none>'}")
    print(f"Gate cleared: {'yes' if not gate['required'] else 'no'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"Attention-repo JIT context assembler (v{ATTENTION_VERSION})")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init_cfg = sub.add_parser("init-config", help="Create central attention-repo config")
    p_init_cfg.add_argument("--force", action="store_true", help="Overwrite existing config")

    p_init = sub.add_parser("init", help="Initialize projects and central index")
    p_init.add_argument("repo", nargs="?", help="Optional direct project path for legacy per-repo init")
    p_init.add_argument("--include-skills", action="store_true", help="Include workspace skills when scanning")
    p_init.add_argument("--include-plugins", action="store_true", help="Include plugin roots when scanning")
    p_init.add_argument("--dry-run", action="store_true", help="Report candidate projects without writing files")

    p_decl = sub.add_parser("declare-intent", help="Declare architectural intent before edits")
    p_decl.add_argument("repo")
    p_decl.add_argument("--affected-entities", required=True, help="Comma-separated entity IDs")
    p_decl.add_argument("--deployment-pipeline", required=True)
    p_decl.add_argument("--first-principle-summary", required=True)
    p_decl.add_argument("--requires-new-entity", required=True, help="true/false")
    p_decl.add_argument("--task-type", choices=["code", "docs", "tests"], default="code")

    p_asm = sub.add_parser("assemble", help="Build gated context payload")
    p_asm.add_argument("repo")

    p_update = sub.add_parser("update-task", help="Overwrite CURRENT_TASK.md with current status")
    p_update.add_argument("repo")
    p_update.add_argument("--status-markdown", required=True)

    p_reg = sub.add_parser("register-new-entity", help="Append a new entity to !MAP.md registry")
    p_reg.add_argument("repo")
    p_reg.add_argument("--id", required=True)
    p_reg.add_argument("--type", required=True)
    p_reg.add_argument("--file-path", required=True)
    p_reg.add_argument("--ci-cd", required=True)
    p_reg.add_argument("--endpoint", required=True)
    p_reg.add_argument("--description", required=True)

    p_fin = sub.add_parser("finalize-change", help="Write deterministic finalize report")
    p_fin.add_argument("repo")
    p_fin.add_argument("--tests-command", default="not_provided")
    p_fin.add_argument("--tests-result", choices=["pass", "fail", "not_run"], default="not_run")
    p_fin.add_argument("--notes", default="none")

    p_fresh = sub.add_parser("map-freshness-check", help="Verify !MAP.md entity metadata matches implementation")
    p_fresh.add_argument("repo")
    p_fresh.add_argument("--no-change-justification", default="", help="Justification if !MAP.md update not needed")

    p_clear = sub.add_parser("clear-task", help="Clear CURRENT_TASK.md")
    p_clear.add_argument("repo")

    p_reinit = sub.add_parser("reinit", help="Archive broken task/map state and rebuild templates safely")
    p_reinit.add_argument("repo")
    p_reinit.add_argument("--salvage-task", action="store_true", default=True, help="Preserve readable CURRENT_TASK.md content")
    p_reinit.add_argument("--no-salvage-task", action="store_false", dest="salvage_task")
    p_reinit.add_argument("--auto-assemble", action="store_true", default=True, help="Run assemble after recovery when declaration remains valid")
    p_reinit.add_argument("--no-auto-assemble", action="store_false", dest="auto_assemble")

    p_release = sub.add_parser("release-attention", help="Mark repo attention as released after wrap")
    p_release.add_argument("repo")
    p_release.add_argument("--note", default="Released attention.")

    p_sync = sub.add_parser("sync-state", help="Sync !MAP.md, CURRENT_TASK.md, and index with timestamps")
    p_sync.add_argument("repo")
    p_sync.add_argument("--version", default=None, help="Version to record; defaults to version.json")
    p_sync.add_argument("--description", default="", help="Description of current state")

    sub.add_parser("bootstrap-update", help="Validate local skill memory and compile the control plane for the deployed version")

    p_repair = sub.add_parser("repair", help="Backfill missing project files for registered projects")

    p_reindex = sub.add_parser("reindex", help="Refresh the central attention-repo index")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init-config":
        cmd_init_config(args)
        return

    if args.command == "init":
        if args.repo:
            repo = resolve_repo(args.repo)
            ensure_templates(repo)
            print(f"Initialized: {repo / '!MAP.md'}")
            print(f"Initialized: {repo / 'CURRENT_TASK.md'}")
            return
        cmd_init_workspace(args)
        return

    if args.command == "declare-intent":
        cmd_declare_intent(args)
        return

    if args.command == "assemble":
        cmd_assemble(args)
        return

    if args.command == "update-task":
        cmd_update_task(args)
        return

    if args.command == "register-new-entity":
        cmd_register_new_entity(args)
        return

    if args.command == "map-freshness-check":
        cmd_map_freshness_check(args)
        return

    if args.command == "finalize-change":
        cmd_finalize_change(args)
        return

    if args.command == "clear-task":
        cmd_clear_task(args)
        return

    if args.command == "reinit":
        cmd_reinit(args)
        return

    if args.command == "release-attention":
        cmd_release_attention(args)
        return

    if args.command == "sync-state":
        cmd_sync_state(args)
        return

    if args.command == "bootstrap-update":
        cmd_bootstrap_update(args)
        return

    if args.command == "repair":
        cmd_repair(args)
        return

    if args.command == "reindex":
        cmd_reindex(args)
        return

    raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
