#!/usr/bin/env python3
"""
state-manager.py - Read and write !CONNECTIONS.md

Manages the human-readable connection notes that bridge
human documentation and AI context.
"""

import re
from datetime import datetime
from pathlib import Path

def read_connections(project_path: str) -> dict:
    """Read !CONNECTIONS_{repo}.md and parse into structured data."""
    
    repo_name = Path(project_path).name
    connections_path = Path(project_path) / f'!CONNECTIONS_{repo_name}.md'
    
    if not connections_path.exists():
        return {'exists': False, 'content': None}
    
    content = connections_path.read_text()
    
    # Simple parsing - extract sections
    sections = {}
    current_section = None
    current_content = []
    
    for line in content.split('\n'):
        if line.startswith('## '):
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = line[3:].strip()
            current_content = []
        else:
            current_content.append(line)
    
    if current_section:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return {
        'exists': True,
        'content': content,
        'sections': sections,
        'path': str(connections_path)
    }

def create_template(project_path: str) -> str:
    """Create a new !CONNECTIONS_{repo}.md template."""
    
    repo_name = Path(project_path).name
    template = f"""# !CONNECTIONS_{repo_name}.md — How Brad Maps Your Context

*This file is written by Brad, read by both of us. It shows how your anchors connect in my attention space.*

---

## Current Scope

**Active Intent:** [What we're working on right now]

**Mood/Tone:** [How the work felt]

**Blockers:** [What paused progress]

---

## Anchor Map

| Anchor | Type | Connects To | Why It Resonates |
|--------|------|-------------|------------------|
| `!MAP.md` | Gate | All sessions | Source of truth |
| `[your-note]` | [type] | [connections] | [reason] |

---

## Attention Paths

When you say: "[example request]"
I read:     !MAP.md → [path]
I propose:  [what I suggest]
You pick:   [your decision]

---

## Discards

*What I filtered out this session:*

- `[file/anchor]` — [why I discarded it]

---

## Uncertainty Log

*Where I'm fuzzy — needs your input:*

- "[question]" — [why it matters]

---

*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} by Brad*
*Next: Your turn to correct, expand, or redirect*
"""
    
    connections_path = Path(project_path) / f'!CONNECTIONS_{repo_name}.md'
    connections_path.write_text(template)
    
    return str(connections_path)

def update_section(project_path: str, section: str, content: str) -> str:
    """Update a specific section in !CONNECTIONS_{repo}.md."""
    
    repo_name = Path(project_path).name
    connections_path = Path(project_path) / f'!CONNECTIONS_{repo_name}.md'
    
    if not connections_path.exists():
        create_template(project_path)
    
    existing = connections_path.read_text()
    
    # Find and replace section
    pattern = rf'(## {re.escape(section)}\n)(.*?)(?=\n## |$)'
    replacement = f'\\1{content}\n'
    
    new_content = re.sub(pattern, replacement, existing, flags=re.DOTALL)
    
    # Update timestamp
    new_content = re.sub(
        r'\*Last updated: .*?\*',
        f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} by Brad*",
        new_content
    )
    
    connections_path.write_text(new_content)
    
    return str(connections_path)

def check_tldr(project_path: str) -> dict:
    """Validate TLDR.md exists (gate check per SKILL.md)."""
    tldr_path = Path(project_path) / 'TLDR.md'
    
    result = {
        'exists': tldr_path.exists(),
        'path': str(tldr_path),
        'warning': None
    }
    
    if not tldr_path.exists():
        result['warning'] = (
            "⚠️  TLDR.md not found! Per attention-layer SKILL.md: "
            "'If TLDR.md doesn't exist, ask the human before proceeding.'"
        )
    
    return result

def read_tldr(project_path: str) -> dict:
    """Read TLDR.md content."""
    tldr_path = Path(project_path) / 'TLDR.md'
    
    if not tldr_path.exists():
        return {
            'exists': False,
            'content': None,
            'path': str(tldr_path)
        }
    
    return {
        'exists': True,
        'content': tldr_path.read_text(),
        'path': str(tldr_path)
    }

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: state-manager.py <command> [args]")
        print("\nCommands:")
        print("  read <project_path>                    - Read !CONNECTIONS_{repo}.md")
        print("  init <project_path>                    - Create !CONNECTIONS_{repo}.md template")
        print("  update <project_path> <section> <content>  - Update section")
        print("  check-tldr <project_path>              - Validate TLDR.md exists (gate check)")
        print("  read-tldr <project_path>               - Read TLDR.md content")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'read':
        result = read_connections(sys.argv[2])
        print(f"Exists: {result['exists']}")
        if result['exists']:
            print(f"Path: {result['path']}")
            print(f"Sections: {list(result['sections'].keys())}")
    
    elif command == 'init':
        path = create_template(sys.argv[2])
        print(f"Created: {path}")
    
    elif command == 'update':
        path = update_section(sys.argv[2], sys.argv[3], sys.argv[4])
        print(f"Updated: {path}")
    
    elif command == 'check-tldr':
        result = check_tldr(sys.argv[2])
        print(f"TLDR exists: {result['exists']}")
        print(f"Path: {result['path']}")
        if result['warning']:
            print(f"\n{result['warning']}")
        sys.exit(0 if result['exists'] else 1)
    
    elif command == 'read-tldr':
        result = read_tldr(sys.argv[2])
        print(f"Exists: {result['exists']}")
        print(f"Path: {result['path']}")
        if result['exists']:
            print("\n--- TLDR.md CONTENT ---")
            print(result['content'])

if __name__ == '__main__':
    main()
