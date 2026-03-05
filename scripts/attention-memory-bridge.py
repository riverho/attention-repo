#!/usr/bin/env python3
"""
attention-memory-bridge.py — Bidirectional Attention-Memory Sync

Features:
1. Auto-significance detection for attention events
2. TLDR/!CONNECTIONS → Memory sync
3. Memory-enriched attention views

Usage:
  attention-memory-bridge sync --project summon
  attention-memory-bridge enrich --project summon
  attention-memory-bridge detect --file TLDR.md
  attention-memory-bridge watch  # Continuous monitoring
"""

import json
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# Paths
WORKSPACE = Path.home() / ".openclaw" / "workspace"
PROJECTS_ROOT = WORKSPACE / "projects"
MEMORY_DIR = WORKSPACE / "memory"
MEMORY_FILE = WORKSPACE / "MEMORY.md"
ATTENTION_STATE = WORKSPACE / ".attention-state"
BRIDGE_STATE = ATTENTION_STATE / "memory-bridge-state.json"


class SignificanceDetector:
    """Detect significance of attention layer changes."""
    
    # Significance scores
    SCORES = {
        # Completion milestones
        r"100%\s*(?:complete|done|finished)": 0.95,
        r"(?:phase|stage)\s*\d+\s*(?:complete|done)": 0.90,
        r"(?:status|grade):\s*A[+-]?": 0.88,
        
        # Architecture decisions
        r"architecture\s+(?:locked|decided|finalized)": 0.95,
        r"(?:decision|choice):\s*(?:use|adopt|implement)": 0.90,
        r"3-layer|3-tier|architecture": 0.85,
        
        # Pivots/changes
        r"/pivot|pivoting|switched\s+to": 0.85,
        r"/branch\s+\w+": 0.60,
        r"abandoned|deprecated|removed": 0.80,
        
        # Blockers resolved
        r"blocker.*resolved|unblocked": 0.82,
        r"(?:issue|bug)\s*#?\d+.*fixed": 0.75,
        
        # Deployments/releases
        r"deployed|released|published": 0.85,
        r"production|live|shipped": 0.88,
        
        # New capabilities
        r"implemented|built|created": 0.70,
        r"MCP|HTTP|WebSocket|API": 0.65,
        
        # Default
        "default": 0.50,
    }
    
    @classmethod
    def detect(cls, content: str, change_type: str = "update") -> Tuple[float, str]:
        """
        Detect significance of content change.
        Returns: (score, reason)
        """
        content_lower = content.lower()
        max_score = 0.0
        matched_pattern = "default"
        
        for pattern, score in cls.SCORES.items():
            if pattern == "default":
                continue
            if re.search(pattern, content_lower, re.IGNORECASE):
                if score > max_score:
                    max_score = score
                    matched_pattern = pattern
        
        # Boost for creation vs update
        if change_type == "create":
            max_score = min(1.0, max_score + 0.1)
        
        # Cap at 0.5 if no strong signals
        if max_score == 0.0:
            max_score = cls.SCORES["default"]
        
        reason = cls._generate_reason(matched_pattern, max_score)
        return max_score, reason
    
    @classmethod
    def _generate_reason(cls, pattern: str, score: float) -> str:
        """Generate human-readable reason for significance."""
        reasons = {
            r"100%\s*(?:complete|done|finished)": "Phase completion (100%)",
            r"(?:phase|stage)\s*\d+\s*(?:complete|done)": "Phase completion",
            r"(?:status|grade):\s*A[+-]?": "High grade achievement",
            r"architecture\s+(?:locked|decided|finalized)": "Architecture decision",
            r"(?:decision|choice):\s*(?:use|adopt|implement)": "Key decision made",
            r"3-layer|3-tier|architecture": "Architecture pattern",
            r"/pivot|pivoting|switched\s+to": "Strategy pivot",
            r"/branch\s+\w+": "New workstream branch",
            r"abandoned|deprecated|removed": "Feature/component removal",
            r"blocker.*resolved|unblocked": "Blocker resolved",
            r"(?:issue|bug)\s*#?\d+.*fixed": "Bug fix",
            r"deployed|released|published": "Deployment/release",
            r"production|live|shipped": "Production deployment",
            r"implemented|built|created": "New implementation",
            r"MCP|HTTP|WebSocket|API": "Protocol/API work",
            "default": "Standard update",
        }
        return reasons.get(pattern, "Significant change detected")
    
    @classmethod
    def should_curate(cls, score: float) -> bool:
        """Whether this should be curated to MEMORY.md."""
        return score >= 0.85
    
    @classmethod
    def should_log(cls, score: float) -> bool:
        """Whether this should be logged to daily memory."""
        return score >= 0.50


class AttentionMemoryBridge:
    """Bridge between attention layer and memory layer."""
    
    def __init__(self):
        self.state = self._load_state()
        self.detector = SignificanceDetector()
    
    def _load_state(self) -> Dict:
        """Load bridge state (tracked file hashes)."""
        if BRIDGE_STATE.exists():
            return json.loads(BRIDGE_STATE.read_text())
        return {"tracked_files": {}, "last_sync": None}
    
    def _save_state(self):
        """Save bridge state."""
        BRIDGE_STATE.parent.mkdir(parents=True, exist_ok=True)
        BRIDGE_STATE.write_text(json.dumps(self.state, indent=2))
    
    def _file_hash(self, path: Path) -> str:
        """Get hash of file content."""
        if not path.exists():
            return ""
        content = path.read_text()
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_daily_memory_path(self) -> Path:
        """Get today's daily memory file."""
        today = datetime.now().strftime("%Y-%m-%d")
        return MEMORY_DIR / f"{today}.md"
    
    def detect_changes(self, project: str) -> List[Dict]:
        """
        Detect changes in attention files for a project.
        Returns list of changes with significance.
        """
        changes = []
        project_path = PROJECTS_ROOT / project
        
        if not project_path.exists():
            return changes
        
        # Files to monitor
        attention_files = [
            (project_path / "TLDR.md", "tldr"),
            (project_path / f"!CONNECTIONS_{project}.md", "connections"),
            (PROJECTS_ROOT / f"!MAP_{project}.md", "map"),
        ]
        
        for file_path, file_type in attention_files:
            if not file_path.exists():
                continue
            
            current_hash = self._file_hash(file_path)
            tracked = self.state["tracked_files"].get(str(file_path), {})
            
            # Check if changed
            if tracked.get("hash") != current_hash:
                content = file_path.read_text() if file_path.exists() else ""
                is_new = tracked.get("hash") is None
                
                # Detect significance
                score, reason = self.detector.detect(
                    content, 
                    "create" if is_new else "update"
                )
                
                change = {
                    "project": project,
                    "file": str(file_path),
                    "type": file_type,
                    "change_type": "create" if is_new else "update",
                    "significance": score,
                    "reason": reason,
                    "content_preview": content[:500] if content else "",
                    "timestamp": datetime.now().isoformat(),
                }
                changes.append(change)
                
                # Update tracked state
                self.state["tracked_files"][str(file_path)] = {
                    "hash": current_hash,
                    "last_sync": datetime.now().isoformat(),
                    "significance": score,
                }
        
        return changes
    
    def sync_to_memory(self, changes: List[Dict]) -> List[str]:
        """
        Sync attention changes to memory layer.
        Returns list of actions taken.
        """
        actions = []
        
        # Group by significance
        high_significance = [c for c in changes if self.detector.should_curate(c["significance"])]
        medium_significance = [c for c in changes if self.detector.should_log(c["significance"]) and not self.detector.should_curate(c["significance"])]
        
        # High significance → Daily memory + Curate
        for change in high_significance:
            # Add to daily memory
            self._append_to_daily_memory(change)
            actions.append(f"Logged to daily memory (significance: {change['significance']:.2f}): {change['reason']}")
            
            # Curate to MEMORY.md
            if self._curate_to_memory(change):
                actions.append(f"Curated to MEMORY.md: {change['project']} - {change['reason']}")
        
        # Medium significance → Daily memory only
        for change in medium_significance:
            self._append_to_daily_memory(change)
            actions.append(f"Logged to daily memory: {change['project']} update")
        
        self._save_state()
        return actions
    
    def _append_to_daily_memory(self, change: Dict):
        """Append change to today's daily memory file."""
        daily_path = self._get_daily_memory_path()
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        
        # Format entry
        entry = f"""
## {datetime.now().strftime('%H:%M')} — {change['project']} Attention Update

**Type:** {change['type']} {change['change_type']}
**Significance:** {change['significance']:.2f}/1.0
**Reason:** {change['reason']}

**Content Preview:**
```
{change['content_preview'][:300]}...
```

---
"""
        
        # Append
        mode = 'a' if daily_path.exists() else 'w'
        with open(daily_path, mode) as f:
            if mode == 'w':
                f.write(f"# Session: {datetime.now().strftime('%Y-%m-%d')}\n\n")
            f.write(entry)
    
    def _curate_to_memory(self, change: Dict) -> bool:
        """
        Curate high-significance change to MEMORY.md.
        Returns True if added.
        """
        if not MEMORY_FILE.exists():
            return False
        
        memory_content = MEMORY_FILE.read_text()
        
        # Check if already recorded (avoid duplicates)
        if change['reason'] in memory_content and change['project'] in memory_content:
            return False
        
        # Create memory entry
        entry = f"""
### {change['project']} — {change['reason']}
**Date:** {datetime.now().strftime('%Y-%m-%d')}
**Significance:** {change['significance']:.2f}

{change['content_preview'][:200]}...

*Source: {change['type']} update*
"""
        
        # Find appropriate section (by project or add new)
        if f"## {change['project']}" in memory_content:
            # Add to existing section
            section_marker = f"## {change['project']}"
            parts = memory_content.split(section_marker, 1)
            if len(parts) == 2:
                # Insert after section header
                new_content = parts[0] + section_marker + entry + parts[1]
                MEMORY_FILE.write_text(new_content)
                return True
        
        # Add new section at end
        with open(MEMORY_FILE, 'a') as f:
            f.write(f"\n## {change['project']}\n\n{entry}\n")
        
        return True
    
    def enrich_attention_view(self, project: str) -> Dict:
        """
        Enrich attention view with relevant memory context.
        Returns enriched view.
        """
        project_path = PROJECTS_ROOT / project
        tldr_path = project_path / "TLDR.md"
        
        if not tldr_path.exists():
            return {"error": "TLDR not found"}
        
        tldr_content = tldr_path.read_text()
        
        # Extract active stream for search
        active_stream_match = re.search(r'\*\*Active Stream:\*\*\s*(.+)', tldr_content)
        active_stream = active_stream_match.group(1) if active_stream_match else ""
        
        # Search memory for relevant context
        memory_context = self._search_memory(project, active_stream)
        
        # Build enriched view
        enriched = {
            "project": project,
            "tldr": tldr_content,
            "memory_context": memory_context,
            "suggested_actions": self._suggest_actions(project, tldr_content, memory_context),
        }
        
        return enriched
    
    def _search_memory(self, project: str, query: str) -> List[Dict]:
        """Search memory for relevant context."""
        results = []
        
        # Search daily memory files (last 30 days)
        cutoff = datetime.now() - timedelta(days=30)
        
        for mem_file in MEMORY_DIR.glob("*.md"):
            try:
                # Parse date from filename
                file_date = datetime.strptime(mem_file.stem, "%Y-%m-%d")
                if file_date < cutoff:
                    continue
                
                content = mem_file.read_text()
                
                # Check if mentions project or query terms
                if project.lower() in content.lower():
                    # Extract relevant sections
                    sections = content.split("## ")
                    for section in sections[1:]:  # Skip header
                        if project.lower() in section.lower():
                            results.append({
                                "date": file_date.strftime("%Y-%m-%d"),
                                "source": str(mem_file),
                                "preview": section[:300],
                            })
                            break
                
            except (ValueError, IOError):
                continue
        
        # Search MEMORY.md
        if MEMORY_FILE.exists():
            memory_content = MEMORY_FILE.read_text()
            if project.lower() in memory_content.lower():
                # Extract project section
                project_section = re.search(
                    rf"## {re.escape(project)}.*?(?=\n## |$)",
                    memory_content,
                    re.DOTALL | re.IGNORECASE
                )
                if project_section:
                    results.append({
                        "date": "curated",
                        "source": "MEMORY.md",
                        "preview": project_section.group(0)[:300],
                    })
        
        return results[:5]  # Return top 5
    
    def _suggest_actions(self, project: str, tldr: str, memory: List[Dict]) -> List[str]:
        """Suggest actions based on attention-memory gap."""
        suggestions = []
        
        # Check if TLDR stale compared to memory
        if memory:
            latest_memory = memory[0]
            if "complete" in latest_memory.get("preview", "").lower():
                if "complete" not in tldr.lower():
                    suggestions.append(f"TLDR may be stale — memory shows completion")
        
        # Check for missing !CONNECTIONS
        connections_path = PROJECTS_ROOT / project / f"!CONNECTIONS_{project}.md"
        if not connections_path.exists():
            suggestions.append("Create !CONNECTIONS file for active session tracking")
        
        return suggestions
    
    def sync_project(self, project: str) -> Dict:
        """
        Full sync for a project.
        Returns sync results.
        """
        changes = self.detect_changes(project)
        actions = self.sync_to_memory(changes) if changes else []
        
        return {
            "project": project,
            "changes_detected": len(changes),
            "actions_taken": actions,
            "high_significance": len([c for c in changes if c["significance"] >= 0.85]),
        }
    
    def watch(self, interval: int = 300):
        """
        Continuous monitoring mode.
        Checks all projects every `interval` seconds.
        """
        import time
        
        print(f"🔍 Attention-Memory Bridge: Watching all projects (interval: {interval}s)")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning...")
                
                for project_dir in PROJECTS_ROOT.iterdir():
                    if not project_dir.is_dir():
                        continue
                    if project_dir.name.startswith('.'):
                        continue
                    
                    result = self.sync_project(project_dir.name)
                    if result["changes_detected"] > 0:
                        print(f"  {project_dir.name}: {result['changes_detected']} changes")
                        for action in result["actions_taken"]:
                            print(f"    → {action}")
                
                print()
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n👋 Stopping watch mode")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Attention-Memory Bridge")
    subparsers = parser.add_subparsers(dest="command")
    
    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync project attention → memory")
    sync_parser.add_argument("--project", "-p", required=True, help="Project name")
    
    # Enrich command
    enrich_parser = subparsers.add_parser("enrich", help="Enrich attention with memory")
    enrich_parser.add_argument("--project", "-p", required=True, help="Project name")
    
    # Detect command
    detect_parser = subparsers.add_parser("detect", help="Detect significance of file")
    detect_parser.add_argument("--file", "-f", required=True, help="File path")
    
    # Watch command
    watch_parser = subparsers.add_parser("watch", help="Continuous monitoring")
    watch_parser.add_argument("--interval", "-i", type=int, default=300, help="Seconds between scans")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show bridge status")
    
    args = parser.parse_args()
    
    bridge = AttentionMemoryBridge()
    
    if args.command == "sync":
        result = bridge.sync_project(args.project)
        print(json.dumps(result, indent=2))
    
    elif args.command == "enrich":
        enriched = bridge.enrich_attention_view(args.project)
        print(f"# Enriched View: {args.project}\n")
        print("## Memory Context:")
        for ctx in enriched.get("memory_context", []):
            print(f"\n**{ctx['date']}** ({ctx['source']}):")
            print(f"```\n{ctx['preview'][:200]}...\n```")
        
        if enriched.get("suggested_actions"):
            print("\n## Suggested Actions:")
            for action in enriched["suggested_actions"]:
                print(f"- {action}")
    
    elif args.command == "detect":
        file_path = Path(args.file)
        if file_path.exists():
            content = file_path.read_text()
            score, reason = SignificanceDetector.detect(content)
            print(f"Significance: {score:.2f}/1.0")
            print(f"Reason: {reason}")
            print(f"Should curate: {SignificanceDetector.should_curate(score)}")
        else:
            print(f"File not found: {args.file}")
    
    elif args.command == "watch":
        bridge.watch(args.interval)
    
    elif args.command == "status":
        print("Attention-Memory Bridge Status")
        print(f"State file: {BRIDGE_STATE}")
        print(f"Tracked files: {len(bridge.state.get('tracked_files', {}))}")
        print(f"Last sync: {bridge.state.get('last_sync', 'Never')}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
