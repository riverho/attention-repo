#!/usr/bin/env python3
"""
self-attention.py — Self-Managed Attention Layer

The attention layer currently requires human to trigger /commands.
This adds self-monitoring so the agent manages its own attention.

When to use:
- Agent detects workstream degradation
- Agent auto-triggers /evaluate or /pivot
- Human approves/rejects (still human gate, but agent-initiated)
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

ATTENTION_STATE_DIR = Path.home() / ".openclaw" / "workspace" / ".attention-state"
GOALS_FILE = ATTENTION_STATE_DIR / "agent-goals.json"


def load_goals():
    """Load all tracked agent goals."""
    if not GOALS_FILE.exists():
        return {}
    return json.loads(GOALS_FILE.read_text())


def save_goals(goals):
    """Save agent goals with metrics."""
    GOALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    GOALS_FILE.write_text(json.dumps(goals, indent=2))


def evaluate_goal(goal_id: str, goals: dict) -> dict:
    """
    Self-evaluate a goal and return recommended action.
    
    Mirrors the TypeScript SelfMonitor logic.
    """
    goal = goals.get(goal_id, {})
    metrics = goal.get('metrics', {})
    thresholds = goal.get('thresholds', {})
    
    issues = []
    
    # Check success rate
    success_rate = metrics.get('tool_success_rate', 1.0)
    min_success = thresholds.get('min_success_rate', 0.7)
    if success_rate < min_success:
        issues.append(f"Success rate {success_rate:.1%} below {min_success:.1%}")
    
    # Check human interventions
    interventions = metrics.get('human_interventions', 0)
    max_interventions = thresholds.get('max_interventions', 3)
    if interventions >= max_interventions:
        issues.append(f"Too many interventions ({interventions})")
    
    # Decide action
    if len(issues) == 0:
        return {
            'health': 'healthy',
            'action': 'continue',
            'confidence': 0.9,
            'reasoning': 'All metrics healthy'
        }
    elif interventions >= max_interventions:
        return {
            'health': 'failing',
            'action': '/pivot',
            'confidence': 0.8,
            'primary_issue': issues[0],
            'reasoning': f"Strategy failing: {'; '.join(issues)}"
        }
    elif len(issues) >= 2:
        return {
            'health': 'degraded',
            'action': '/evaluate',
            'confidence': 0.7,
            'primary_issue': issues[0],
            'reasoning': f"Multiple issues: {'; '.join(issues)}"
        }
    else:
        return {
            'health': 'degraded',
            'action': '/branch',
            'confidence': 0.6,
            'primary_issue': issues[0],
            'reasoning': f"Single issue: {issues[0]}"
        }


def auto_ster(goal_id: str) -> dict:
    """
    Auto-trigger attention routing based on self-evaluation.
    
    Returns proposal for human approval.
    """
    goals = load_goals()
    evaluation = evaluate_goal(goal_id, goals)
    
    if evaluation['action'] == 'continue':
        return {
            'triggered': False,
            'message': 'Goal healthy, no action needed'
        }
    
    # Build proposal
    goal = goals.get(goal_id, {})
    proposals = {
        '/evaluate': {
            'message': f"⚡ Agent-initiated /evaluate",
            'proposal': f"Self-monitoring detected degradation in '{goal_id}': {evaluation['reasoning']}. Recommend running attention funnel to analyze alternatives.",
            'human_gate': True
        },
        '/pivot': {
            'message': f"⚡ Agent-initiated /pivot",
            'proposal': f"Strategy failing after {goal.get('metrics', {}).get('human_interventions', 0)} interventions. Recommend pivoting: {evaluation['primary_issue']}",
            'human_gate': True
        },
        '/branch': {
            'message': f"⚡ Agent-initiated /branch",
            'proposal': f"Performance degraded: {evaluation['reasoning']}. Recommend branching to parallel workstream.",
            'human_gate': True
        }
    }
    
    result = proposals.get(evaluation['action'], {
        'message': 'Unknown action',
        'proposal': 'Manual review needed',
        'human_gate': True
    })
    
    result.update({
        'triggered': True,
        'action': evaluation['action'],
        'evaluation': evaluation
    })
    
    return result


def create_goal(goal_id: str, objective: str, thresholds: dict = None):
    """Create a new self-monitoring goal."""
    goals = load_goals()
    
    goals[goal_id] = {
        'id': goal_id,
        'objective': objective,
        'created': datetime.now().isoformat(),
        'thresholds': thresholds or {
            'min_success_rate': 0.7,
            'max_latency': 5000,
            'max_interventions': 3
        },
        'metrics': {
            'tool_success_rate': 1.0,
            'average_latency': 0,
            'human_interventions': 0,
            'replanning_events': 0,
            'execution_count': 0,
            'last_evaluated': datetime.now().isoformat()
        }
    }
    
    save_goals(goals)
    print(f"✅ Created self-monitoring goal: {goal_id}")
    print(f"   Objective: {objective}")


def list_goals():
    """List all goals with health status."""
    goals = load_goals()
    
    if not goals:
        print("No agent goals configured.")
        return
    
    print("\n🤖 Agent Goals:\n")
    for goal_id, goal in goals.items():
        evaluation = evaluate_goal(goal_id, goals)
        
        health_icon = {
            'healthy': '🟢',
            'degraded': '🟡',
            'failing': '🔴'
        }.get(evaluation['health'], '⚪')
        
        print(f"  {health_icon} {goal_id}")
        print(f"     Objective: {goal['objective'][:50]}...")
        print(f"     Health: {evaluation['health']}")
        print(f"     Action: {evaluation['action']}")
        print()


def check_goal(goal_id: str):
    """Check goal health and propose action."""
    goals = load_goals()
    
    if goal_id not in goals:
        print(f"Goal '{goal_id}' not found")
        return
    
    evaluation = evaluate_goal(goal_id, goals)
    
    print(f"\n🏥 Goal Health: {goal_id}\n")
    print(f"   Status: {evaluation['health'].upper()}")
    print(f"   Confidence: {evaluation['confidence']:.0%}")
    print(f"   Recommended: {evaluation['action']}")
    
    if evaluation.get('primary_issue'):
        print(f"   Issue: {evaluation['primary_issue']}")
    
    print(f"   Reasoning: {evaluation['reasoning']}")
    
    # Auto-steer proposal
    if evaluation['action'] != 'continue':
        result = auto_ster(goal_id)
        print(f"\n💡 Agent Proposal:")
        print(f"   {result['proposal']}")
        print(f"\n   Run: attention self-apply {goal_id}")


def self_apply(goal_id: str, approve: bool = False):
    """
    Apply agent's self-recommended action.
    
    If approve=True, executes. If False, shows proposal for human approval.
    """
    result = auto_ster(goal_id)
    
    if not result['triggered']:
        print(result['message'])
        return
    
    print(result['message'])
    print(f"\nProposal:")
    print(f"  {result['proposal']}")
    
    if result.get('human_gate') and not approve:
        print("\n⚠️  Human approval required.")
        print(f"Run: attention self-apply {goal_id} --approve")
        return
    
    # Execute the action
    action = result['action']
    print(f"\n✅ Executing: {action}")
    
    # Here we would actually trigger the attention command
    # For now, just log it
    print(f"   (Would trigger: {action})")
    
    # Reset metrics after pivot
    if action == '/pivot':
        goals = load_goals()
        goals[goal_id]['metrics']['human_interventions'] = 0
        goals[goal_id]['metrics']['replanning_events'] += 1
        save_goals(goals)
        print("   Metrics reset for new strategy")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: self-attention.py <command> [args]")
        print("\nCommands:")
        print("  create <goal_id> <objective>    Create new self-monitoring goal")
        print("  list                            List all goals with health")
        print("  check <goal_id>                 Check goal health")
        print("  apply <goal_id> [--approve]     Apply agent's recommendation")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == 'create':
        if len(sys.argv) < 4:
            print("Usage: self-attention.py create <goal_id> <objective>")
            sys.exit(1)
        create_goal(sys.argv[2], sys.argv[3])
    
    elif cmd == 'list':
        list_goals()
    
    elif cmd == 'check':
        if len(sys.argv) < 3:
            print("Usage: self-attention.py check <goal_id>")
            sys.exit(1)
        check_goal(sys.argv[2])
    
    elif cmd == 'apply':
        if len(sys.argv) < 3:
            print("Usage: self-attention.py apply <goal_id> [--approve]")
            sys.exit(1)
        approve = '--approve' in sys.argv
        self_apply(sys.argv[2], approve)
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == '__main__':
    main()
