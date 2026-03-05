#!/usr/bin/env python3
"""
attention agent — Self-Managing Ecosystem Agent

The attention-layer as a true agent:
- Scans all projects
- Detects drift/staleness/conflicts
- Auto-organizes ecosystem
- Proposes actions (human gate)

Usage:
  attention-agent scan              # Full ecosystem health check
  attention-agent status            # Show ecosystem dashboard
  attention-agent organize          # Auto-organize (low-risk only)
  attention-agent propose           # Show proposed actions
  attention-agent apply <id>        # Apply proposed action
  attention-agent run               # Full cycle (scan + organize + propose)
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import subprocess

PROJECTS_ROOT = Path.home() / ".openclaw" / "workspace" / "projects"
ATTENTION_STATE = Path.home() / ".openclaw" / "workspace" / ".attention-state"
AGENT_STATE_FILE = ATTENTION_STATE / "attention-agent-state.json"


def load_agent_state():
    """Load attention agent state."""
    if not AGENT_STATE_FILE.exists():
        return {'last_scan': None, 'actions_history': []}
    return json.loads(AGENT_STATE_FILE.read_text())


def save_agent_state(state):
    """Save attention agent state."""
    AGENT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    AGENT_STATE_FILE.write_text(json.dumps(state, indent=2))


def sync_with_memory_bridge(project: str) -> dict:
    """Sync project with attention-memory bridge."""
    try:
        bridge_script = Path(__file__).parent / "attention-memory-bridge.py"
        result = subprocess.run(
            ["python3", str(bridge_script), "sync", "--project", project],
            capture_output=True,
            text=True,
            timeout=10
        )
        return json.loads(result.stdout) if result.returncode == 0 else {}
    except Exception as e:
        return {"error": str(e)}


def enrich_with_memory(project: str) -> dict:
    """Get memory-enriched view of project."""
    try:
        bridge_script = Path(__file__).parent / "attention-memory-bridge.py"
        result = subprocess.run(
            ["python3", str(bridge_script), "enrich", "--project", project],
            capture_output=True,
            text=True,
            timeout=10
        )
        # Parse the text output since enrich doesn't output JSON
        return {"output": result.stdout} if result.returncode == 0 else {"error": result.stderr}
    except Exception as e:
        return {"error": str(e)}


def scan_project(project_path: Path) -> dict:
    """Analyze a single project."""
    name = project_path.name
    stat = project_path.stat()
    
    # Check files
    tldr = (project_path / "TLDR.md").exists()
    connections = (project_path / f"!CONNECTIONS_{name}.md").exists()
    map_file = (PROJECTS_ROOT / f"!MAP_{name}.md").exists()
    
    # Count branches
    branches = len(list(project_path.glob("TLDR_*.md")))
    
    # Determine health
    days_old = (datetime.now().timestamp() - stat.st_mtime) / (24 * 3600)
    
    if days_old > 30:
        health = "abandoned"
    elif days_old > 7:
        health = "stale"
    elif branches > 3:
        health = "conflicted"
    else:
        health = "active"
    
    return {
        'name': name,
        'path': str(project_path),
        'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        'days_inactive': int(days_old),
        'tldr': tldr,
        'connections': connections,
        'map': map_file,
        'branches': branches,
        'health': health
    }


def scan_ecosystem():
    """Scan all projects."""
    projects = []
    
    if not PROJECTS_ROOT.exists():
        print(f"❌ Projects root not found: {PROJECTS_ROOT}")
        return []
    
    for entry in PROJECTS_ROOT.iterdir():
        if not entry.is_dir():
            continue
        if entry.name.startswith('.'):
            continue
        
        projects.append(scan_project(entry))
    
    return projects


def evaluate_ecosystem(projects: list) -> dict:
    """Evaluate overall ecosystem health."""
    total = len(projects)
    active = sum(1 for p in projects if p['health'] == 'active')
    stale = sum(1 for p in projects if p['health'] == 'stale')
    abandoned = sum(1 for p in projects if p['health'] == 'abandoned')
    conflicted = sum(1 for p in projects if p['health'] == 'conflicted')
    
    # Missing TLDRs
    no_tldr = sum(1 for p in projects if not p['tldr'])
    
    if conflicted > 0 or abandoned > total * 0.3:
        overall = "critical"
    elif stale > total * 0.5:
        overall = "degraded"
    else:
        overall = "healthy"
    
    return {
        'total': total,
        'active': active,
        'stale': stale,
        'abandoned': abandoned,
        'conflicted': conflicted,
        'no_tldr': no_tldr,
        'overall': overall
    }


def generate_actions(projects: list, health: dict) -> list:
    """Generate attention actions."""
    actions = []
    action_id = 0
    
    # Update stale TLDRs
    for p in projects:
        if p['health'] == 'stale' and p['tldr']:
            action_id += 1
            actions.append({
                'id': action_id,
                'type': 'update_tldr',
                'target': p['name'],
                'reason': f"{p['days_inactive']} days inactive",
                'proposal': f"Update TLDR.md to reflect current status",
                'auto': False,
                'priority': 'medium'
            })
    
    # Create missing TLDRs
    for p in projects:
        if not p['tldr']:
            action_id += 1
            actions.append({
                'id': action_id,
                'type': 'create_tldr',
                'target': p['name'],
                'reason': "No TLDR.md found",
                'proposal': f"Create TLDR.md for {p['name']}",
                'auto': True,
                'priority': 'high'
            })
    
    # Archive abandoned
    for p in projects:
        if p['health'] == 'abandoned':
            action_id += 1
            actions.append({
                'id': action_id,
                'type': 'archive',
                'target': p['name'],
                'reason': f"{p['days_inactive']} days — likely abandoned",
                'proposal': f"Archive {p['name']} to dormant/",
                'auto': False,
                'priority': 'low'
            })
    
    # Resolve conflicts
    for p in projects:
        if p['health'] == 'conflicted':
            action_id += 1
            actions.append({
                'id': action_id,
                'type': 'merge_branches',
                'target': p['name'],
                'reason': f"{p['branches']} branches — attention fragmentation",
                'proposal': f"Evaluate and merge branches for {p['name']}",
                'auto': False,
                'priority': 'high'
            })
    
    return actions


def cmd_scan():
    """Scan ecosystem and show health."""
    print("🔍 Attention Agent: Scanning ecosystem...\n")
    
    projects = scan_ecosystem()
    health = evaluate_ecosystem(projects)
    
    print(f"Ecosystem Health: {health['overall'].upper()}")
    print(f"\nProjects: {health['total']}")
    print(f"  🟢 Active: {health['active']}")
    print(f"  🟡 Stale: {health['stale']}")
    print(f"  🔴 Abandoned: {health['abandoned']}")
    print(f"  ⚠️  Conflicted: {health['conflicted']}")
    print(f"  ❓ Missing TLDR: {health['no_tldr']}")
    
    if health['overall'] != 'healthy':
        print(f"\n⚡ Run 'attention-agent propose' to see recommended actions")
    
    # Save state
    state = load_agent_state()
    state['last_scan'] = datetime.now().isoformat()
    state['last_health'] = health
    save_agent_state(state)


def cmd_status():
    """Show detailed status."""
    print("📊 Attention Agent: Ecosystem Dashboard\n")
    
    projects = scan_ecosystem()
    
    print(f"{'Project':<30} {'Health':<12} {'Days':<6} {'Branches'}")
    print("-" * 60)
    
    for p in sorted(projects, key=lambda x: x['days_inactive'], reverse=True):
        icon = {
            'active': '🟢',
            'stale': '🟡',
            'abandoned': '🔴',
            'conflicted': '⚠️'
        }.get(p['health'], '⚪')
        
        print(f"{p['name']:<30} {icon} {p['health']:<10} {p['days_inactive']:<6} {p['branches']}")
    
    print()


def cmd_organize():
    """Auto-organize ecosystem."""
    print("🤖 Attention Agent: Auto-organizing...\n")
    
    projects = scan_ecosystem()
    health = evaluate_ecosystem(projects)
    actions = generate_actions(projects, health)
    
    auto_actions = [a for a in actions if a['auto']]
    
    if not auto_actions:
        print("No auto-actions available. Run 'attention-agent propose' for manual actions.")
        return
    
    print(f"Executing {len(auto_actions)} auto-actions:\n")
    
    for action in auto_actions:
        print(f"  {action['type']} on {action['target']}")
        
        if action['type'] == 'create_tldr':
            # Auto-create TLDR
            project_path = PROJECTS_ROOT / action['target']
            tldr_path = project_path / "TLDR.md"
            
            content = f"""# TLDR — {action['target']}

**Status:** Active (auto-detected)
**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}
**Detected By:** Attention Agent

## Notes

This TLDR was auto-created by Attention Agent.
Please update with actual project status.

---
*Auto-generated on {datetime.now().strftime('%Y-%m-%d')}*
"""
            tldr_path.write_text(content)
            print(f"    ✅ Created {tldr_path}")


def cmd_propose():
    """Show proposed actions."""
    print("💡 Attention Agent: Proposed Actions\n")
    
    projects = scan_ecosystem()
    health = evaluate_ecosystem(projects)
    actions = generate_actions(projects, health)
    
    manual_actions = [a for a in actions if not a['auto']]
    
    if not manual_actions:
        print("No actions pending. Ecosystem healthy!")
        return
    
    print(f"{'ID':<5} {'Type':<20} {'Target':<25} {'Priority'}")
    print("-" * 70)
    
    for action in manual_actions:
        print(f"{action['id']:<5} {action['type']:<20} {action['target']:<25} {action['priority']}")
        print(f"      Reason: {action['reason']}")
        print(f"      Proposal: {action['proposal']}")
        print()
    
    print(f"Run 'attention-agent apply <id>' to execute")


def cmd_apply(action_id: str):
    """Apply a proposed action."""
    try:
        action_id = int(action_id)
    except ValueError:
        print(f"Invalid action ID: {action_id}")
        return
    
    projects = scan_ecosystem()
    health = evaluate_ecosystem(projects)
    actions = generate_actions(projects, health)
    
    action = next((a for a in actions if a['id'] == action_id), None)
    
    if not action:
        print(f"Action {action_id} not found")
        return
    
    print(f"⚡ Applying action {action_id}: {action['type']} on {action['target']}")
    print(f"   {action['proposal']}")
    print()
    
    confirm = input("Confirm? [y/N]: ")
    if confirm.lower() != 'y':
        print("Cancelled")
        return
    
    # Execute
    if action['type'] == 'update_tldr':
        project_path = PROJECTS_ROOT / action['target']
        tldr_path = project_path / "TLDR.md"
        
        content = f"""# TLDR — {action['target']}

**Status:** Under Review (updated by Attention Agent)
**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}

## Reason for Update

{action['reason']}

## Recommended Actions

- Review current project status
- Update Active Stream if changed
- Run /evaluate if direction unclear

---
*Updated by Attention Agent on {datetime.now().strftime('%Y-%m-%d')}*
"""
        tldr_path.write_text(content)
        print(f"✅ Updated {tldr_path}")
    
    elif action['type'] == 'archive':
        print(f"📦 Would archive {action['target']} (manual move required)")
    
    elif action['type'] == 'merge_branches':
        print(f"🔀 Would evaluate branches for {action['target']} (manual merge required)")
    
    else:
        print(f"⚠️  Action type '{action['type']}' requires manual execution")


def cmd_run():
    """Full agent cycle."""
    print("🤖 Attention Agent: Full Cycle\n")
    
    cmd_scan()
    print()
    cmd_organize()
    print()
    cmd_propose()


def cmd_sync():
    """Sync all projects with memory bridge."""
    print("🔄 Attention Agent: Syncing with Memory Bridge...\n")
    
    projects = scan_ecosystem()
    
    for project in projects:
        print(f"  Syncing {project['name']}...")
        result = sync_with_memory_bridge(project['name'])
        
        if 'changes_detected' in result:
            if result['changes_detected'] > 0:
                print(f"    ✅ {result['changes_detected']} changes synced")
                for action in result.get('actions_taken', [])[:2]:  # Show first 2
                    print(f"      → {action[:60]}...")
            else:
                print(f"    ✓ No changes")
        else:
            print(f"    ⚠️  Sync skipped")
    
    print("\n✅ Sync complete")


def cmd_enrich(project_name: str = None):
    """Show memory-enriched view of project(s)."""
    if project_name:
        projects = [p for p in scan_ecosystem() if p['name'] == project_name]
        if not projects:
            print(f"Project {project_name} not found")
            return
    else:
        projects = scan_ecosystem()
    
    print("📚 Memory-Enriched Project Views\n")
    
    for project in projects[:3]:  # Show first 3
        print(f"## {project['name']}")
        print(f"Health: {project['health']} | Days inactive: {project['days_inactive']}")
        
        enriched = enrich_with_memory(project['name'])
        if 'output' in enriched:
            # Extract memory context section
            output = enriched['output']
            if 'Memory Context:' in output:
                print("\nRecent History:")
                # Find memory context section
                lines = output.split('\n')
                in_context = False
                for line in lines:
                    if 'Memory Context:' in line:
                        in_context = True
                        continue
                    if in_context and line.strip() and not line.startswith('#'):
                        if line.startswith('**'):
                            print(f"  • {line}")
                        if len(line) > 50:
                            break
        
        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: attention-agent.py <command> [args]")
        print("\nCommands:")
        print("  scan                 Scan ecosystem health")
        print("  status               Show detailed project status")
        print("  organize             Auto-organize (safe actions only)")
        print("  propose              Show proposed actions")
        print("  apply <id>           Apply proposed action")
        print("  sync                 Sync with memory bridge")
        print("  enrich [project]     Show memory-enriched views")
        print("  run                  Full cycle (scan + organize + propose)")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == 'scan':
        cmd_scan()
    elif cmd == 'status':
        cmd_status()
    elif cmd == 'organize':
        cmd_organize()
    elif cmd == 'propose':
        cmd_propose()
    elif cmd == 'apply':
        if len(sys.argv) < 3:
            print("Usage: attention-agent.py apply <id>")
            sys.exit(1)
        cmd_apply(sys.argv[2])
    elif cmd == 'sync':
        cmd_sync()
    elif cmd == 'enrich':
        project = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_enrich(project)
    elif cmd == 'run':
        cmd_run()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == '__main__':
    main()
