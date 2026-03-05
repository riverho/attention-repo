#!/usr/bin/env python3
"""Lean v3 attention engine: first-principles + CI/CD entity mapping gate."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ENTITY_START = "<!-- ENTITY_REGISTRY_START -->"
ENTITY_END = "<!-- ENTITY_REGISTRY_END -->"
ATTN_DIR = ".attention"
DECLARATION_FILE = "architectural_intent.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_git(repo: Path, *args: str) -> str:
    try:
        out = subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.STDOUT)
        return out.decode("utf-8").strip()
    except subprocess.CalledProcessError as exc:
        return f"<git command failed: {' '.join(args)}>\n{exc.output.decode('utf-8', errors='replace').strip()}"


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


def ensure_templates(repo: Path) -> None:
    map_path = repo / "!MAP.md"
    task_path = repo / "CURRENT_TASK.md"

    if not map_path.exists():
        write_text(
            map_path,
            """# !MAP.md

## Purpose
Describe what this repository is for.

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
  "entities": [
    {
      "id": "E-EXAMPLE-01",
      "type": "Endpoint",
      "file_path": "src/example.ts",
      "ci_cd": ".github/workflows/ci.yml",
      "endpoint": "GET /example",
      "description": "Example entity"
    }
  ]
}
<!-- ENTITY_REGISTRY_END -->
""",
        )

    if not task_path.exists():
        write_text(
            task_path,
            """# CURRENT_TASK.md

## Goal
Describe the current task.

## Constraints
- Keep changes minimal
- Preserve existing behavior

## Done When
- [ ] Tests pass
- [ ] Changes committed
""",
        )


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
        if mapped and deployment_pipeline not in mapped:
            allowed = ", ".join(sorted(str(x) for x in mapped))
            raise ValueError(
                "deployment_pipeline must match the selected entity mappings. "
                f"Expected one of: {allowed}"
            )


def cmd_declare_intent(args: argparse.Namespace) -> None:
    repo = Path(args.repo).expanduser().resolve()
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
    repo = Path(args.repo).expanduser().resolve()
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

    print(payload)


def cmd_update_task(args: argparse.Namespace) -> None:
    repo = Path(args.repo).expanduser().resolve()
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
    print(f"Updated: {repo / 'CURRENT_TASK.md'}")


def cmd_register_new_entity(args: argparse.Namespace) -> None:
    repo = Path(args.repo).expanduser().resolve()
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


def cmd_finalize_change(args: argparse.Namespace) -> None:
    repo = Path(args.repo).expanduser().resolve()
    declaration = load_declaration(repo)
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
    print(f"Wrote finalize report: {out}")


def cmd_clear_task(args: argparse.Namespace) -> None:
    repo = Path(args.repo).expanduser().resolve()
    write_text(repo / "CURRENT_TASK.md", "# CURRENT_TASK.md\n\n")
    print(f"Cleared: {repo / 'CURRENT_TASK.md'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lean v3 JIT context assembler")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create !MAP.md and CURRENT_TASK.md templates")
    p_init.add_argument("repo")

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

    p_clear = sub.add_parser("clear-task", help="Clear CURRENT_TASK.md")
    p_clear.add_argument("repo")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init":
        repo = Path(args.repo).expanduser().resolve()
        ensure_templates(repo)
        print(f"Initialized: {repo / '!MAP.md'}")
        print(f"Initialized: {repo / 'CURRENT_TASK.md'}")
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

    if args.command == "finalize-change":
        cmd_finalize_change(args)
        return

    if args.command == "clear-task":
        cmd_clear_task(args)
        return

    raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
