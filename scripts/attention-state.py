#!/usr/bin/env python3
"""CLI wrapper for global attention-state management."""

from __future__ import annotations

import sys

try:
    from scripts.attention_state import get_active, list_attended, release_active, set_active
except ModuleNotFoundError:
    from attention_state import get_active, list_attended, release_active, set_active


def _extract_release_note(args: list[str]) -> str | None:
    if "--note" not in args:
        return None
    index = args.index("--note")
    if index + 1 >= len(args):
        return None
    return args[index + 1]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: attention-state.py <command>")
        print("Commands: get, set <repo_path>, release [--note <text>], list")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "get":
        active = get_active()
        if active:
            print(f"Active: {active['name']} ({active['path']})")
            print(f"Attended at: {active['attended_at']}")
        else:
            print("No active attention")
    elif cmd == "set" and len(sys.argv) >= 3:
        state = set_active(sys.argv[2])
        print(f"📍 Attention set to: {state['active']}")
    elif cmd == "release":
        released, _ = release_active(_extract_release_note(sys.argv[2:]))
        if released.get("name"):
            print(f"📍 Attention released from: {released['name']}")
    elif cmd == "list":
        attended = list_attended()
        if attended:
            for name, info in attended.items():
                print(f"  {name}: {info['path']} (last: {info['last_attended']})")
        else:
            print("No attended repos")
    else:
        print("Unknown command")
        sys.exit(1)
