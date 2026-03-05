#!/usr/bin/env python3
"""
spawn-attention.py - Generate OpenClaw CLI commands for three-layer attention funnel

Usage:
  spawn-attention.py "intent" /path/to/project
  
Generates executable shell commands for the search → plan → synthesize pattern.
State is stored centrally in ~/.openclaw/workspace/.attention-state/ to avoid
polluting project folders.
"""

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

def get_project_slug(project_path: str) -> str:
    """Generate a unique slug for the project based on its absolute path."""
    abs_path = os.path.abspath(project_path)
    # Use folder name + short hash of full path for uniqueness
    folder_name = Path(abs_path).name
    path_hash = hashlib.md5(abs_path.encode()).hexdigest()[:8]
    return f"{folder_name}-{path_hash}"

def get_attention_base_dir() -> Path:
    """Get the centralized attention state directory."""
    base = Path.home() / ".openclaw" / "workspace" / ".attention-state"
    base.mkdir(parents=True, exist_ok=True)
    return base

def get_project_state_dir(project_path: str) -> Path:
    """Get the state directory for a specific project."""
    slug = get_project_slug(project_path)
    state_dir = get_attention_base_dir() / slug
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir

def sanitize_for_shell(text: str) -> str:
    """Escape quotes for safe shell usage."""
    return text.replace('"', '\\"')

def generate_layer_command(layer_num: int, layer_name: str, agent: str, task: str, 
                           project_path: str, state_file: str, artifact_path: str,
                           depends_on: int = None) -> dict:
    """Generate an OpenClaw CLI command for a layer."""
    
    task_escaped = sanitize_for_shell(task)
    state_dir = Path(state_file).parent
    
    cmd_parts = [
        f"# Layer {layer_num}: {layer_name}",
        f"echo 'Running Layer {layer_num}: {layer_name}...'",
        f"mkdir -p {state_dir}",
        f"",
        f"# Spawn agent via OpenClaw CLI",
        f"openclaw sessions spawn {agent} \\",
        f"  \"{task_escaped}\" \\",
        f"  --mode=run \\",
        f"  --label=attention-layer{layer_num} \\",
        f"  --cwd={project_path} \\",
        f"  2>&1 | tee {artifact_path}",
        f"",
        f"# Update state file",
        f"python3 -c \"",
        f"import json",
        f"state = json.load(open('{state_file}'))",
        f"state['layer{layer_num}']['status'] = 'completed'",
        f"state['layer{layer_num}']['artifact'] = '{artifact_path}'",
        f"json.dump(state, open('{state_file}', 'w'), indent=2)",
        f"\"",
        f"",
        f"echo 'Layer {layer_num} complete. Output: {artifact_path}'",
        f""
    ]
    
    if depends_on:
        cmd_parts.insert(1, f"# Depends on: Layer {depends_on}")
    
    return {
        'layer': layer_num,
        'name': layer_name,
        'agent': agent,
        'command': '\n'.join(cmd_parts),
        'artifact': artifact_path,
        'status': 'pending'
    }

def generate_funnel(intent: str, project_path: str) -> dict:
    """Generate all three layers of the attention funnel."""
    
    repo_name = Path(project_path).name
    timestamp = datetime.now().isoformat()
    
    # Centralized state directory (not in project folder)
    state_dir = get_project_state_dir(project_path)
    state_file = state_dir / "funnel-state.json"
    
    # Initial state
    state = {
        'created': timestamp,
        'intent': intent,
        'project': str(project_path),
        'repo': repo_name,
        'project_slug': get_project_slug(project_path),
        'state_dir': str(state_dir),
        'layer1': {'status': 'pending', 'artifact': None},
        'layer2': {'status': 'pending', 'artifact': None},
        'layer3': {'status': 'pending', 'artifact': None},
        'human_gate': 'pending'
    }
    
    state_file.write_text(json.dumps(state, indent=2))
    
    layers = []
    
    # Artifact paths (centralized, not in project)
    artifact1 = state_dir / "layer1-search.log"
    artifact2 = state_dir / "layer2-planner.log"
    artifact3 = state_dir / "layer3-synthesis.log"
    
    # Layer 1: Search
    layers.append(generate_layer_command(
        layer_num=1,
        layer_name="Search",
        agent="codex",
        task=(
            f"Search codebase at {project_path} for files related to: {intent}. "
            f"Return 10-20 candidate files with brief relevance notes. "
            f"Be aggressive in filtering — discard 90% of codebase. "
            f"Output JSON: {{'candidates': [{{'file': 'path', 'relevance': 'why'}}]}}"
        ),
        project_path=project_path,
        state_file=str(state_file),
        artifact_path=str(artifact1)
    ))
    
    # Layer 2: Plan
    layers.append(generate_layer_command(
        layer_num=2,
        layer_name="Planner",
        agent="claude",
        task=(
            f"Read the output from Layer 1 at {artifact1}. "
            f"Given the candidate files, analyze dependencies and identify 3-5 leverage points. "
            f"Output the sequence of changes needed to implement: {intent}"
        ),
        project_path=project_path,
        state_file=str(state_file),
        artifact_path=str(artifact2),
        depends_on=1
    ))
    
    # Layer 3: Synthesize
    layers.append(generate_layer_command(
        layer_num=3,
        layer_name="Synthesis",
        agent="claude",
        task=(
            f"Read !MAP.md and !CONNECTIONS_{repo_name}.md from {project_path}. "
            f"Then read the plan from Layer 2 at {artifact2}. "
            f"Synthesize 3 clear options for human review. Each option: approach, tradeoffs, estimated effort. "
            f"Wait for human choice before proceeding."
        ),
        project_path=project_path,
        state_file=str(state_file),
        artifact_path=str(artifact3),
        depends_on=2
    ))
    
    return {
        'state_file': str(state_file),
        'state_dir': str(state_dir),
        'layers': layers,
        'meta': {
            'created': timestamp,
            'intent': intent,
            'project': str(project_path),
            'project_slug': get_project_slug(project_path)
        }
    }

def generate_shell_script(funnel: dict) -> str:
    """Generate a runnable shell script from the funnel."""
    
    lines = [
        "#!/bin/bash",
        "# Attention Funnel - Generated by spawn-attention.py",
        f"# Intent: {funnel['meta']['intent']}",
        f"# Project: {funnel['meta']['project']}",
        f"# Project Slug: {funnel['meta']['project_slug']}",
        f"# Created: {funnel['meta']['created']}",
        "",
        "set -e  # Exit on error",
        "",
        f"STATE_FILE=\"{funnel['state_file']}\"",
        f"STATE_DIR=\"{funnel['state_dir']}\"",
        "",
        "echo '========================================'",
        "echo '  ATTENTION FUNNEL - Three Layer Flow'",
        "echo '========================================'",
        f"echo 'Project: {funnel['meta']['project']}'",
        f"echo 'State:   {funnel['state_dir']}'",
        "echo ''",
        ""
    ]
    
    for layer in funnel['layers']:
        lines.append(layer['command'])
        lines.append("")
        lines.append("echo ''")
        lines.append("echo '----------------------------------------'")
        lines.append("")
    
    lines.append("echo 'All layers complete.'")
    lines.append("echo ''")
    lines.append(f"echo 'Artifacts: {funnel['state_dir']}'")
    lines.append(f"echo 'State:     {funnel['state_file']}'")
    
    return '\n'.join(lines)

def main():
    if len(sys.argv) < 3:
        print("Usage: spawn-attention.py <intent> <project_path>")
        print("")
        print("Examples:")
        print('  spawn-attention.py "implement auth flow" ./my-project')
        print('  spawn-attention.py "refactor database layer" /path/to/repo')
        print("")
        print("Outputs:")
        print("  - Shell commands to stdout (pipe to file to save)")
        print("  - ~/.openclaw/workspace/.attention-state/{project-slug}/")
        print("    - funnel-state.json (tracks progress)")
        print("    - layer{N}-{name}.log (agent outputs)")
        print("    - run-funnel.sh (generated script)")
        sys.exit(1)
    
    intent = sys.argv[1]
    project_path = os.path.abspath(sys.argv[2])
    
    if not Path(project_path).exists():
        print(f"Error: Project path does not exist: {project_path}")
        sys.exit(1)
    
    # Generate funnel
    funnel = generate_funnel(intent, project_path)
    
    # Output shell script
    script = generate_shell_script(funnel)
    print(script)
    
    # Save to centralized location (not in project folder)
    state_dir = Path(funnel['state_dir'])
    script_path = state_dir / "run-funnel.sh"
    script_path.write_text(script)
    script_path.chmod(0o755)
    
    print(f"\n# Generated files (centralized, not in project folder):")
    print(f"# State dir:  {funnel['state_dir']}")
    print(f"# State file: {funnel['state_file']}")
    print(f"# Script:     {script_path}")
    print(f"# Run with:   bash {script_path}")

if __name__ == '__main__':
    main()
