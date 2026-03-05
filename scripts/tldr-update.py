#!/usr/bin/env python3
"""
tldr-update.py - Compress session context into human-readable TLDR

Reads session artifacts (STATUS.md, REVIEW.md, chat history) and generates
a compressed TLDR.md that captures: intent, outcomes, blockers, next steps.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

def read_session_artifacts(project_path: str) -> dict:
    """Read artifacts from last session."""
    artifacts = {
        'status': None,
        'review': None,
        'timestamp': None
    }
    
    status_path = Path(project_path) / 'STATUS.md'
    review_path = Path(project_path) / 'REVIEW.md'
    
    if status_path.exists():
        artifacts['status'] = status_path.read_text()
        artifacts['timestamp'] = datetime.fromtimestamp(status_path.stat().st_mtime).isoformat()
    
    if review_path.exists():
        artifacts['review'] = review_path.read_text()
    
    return artifacts

def extract_intent(text: str) -> str:
    """Extract human intent from session text."""
    # Look for explicit intent statements
    patterns = [
        r'(?i)intent[:\s]+(.+?)(?:\n|$)',
        r'(?i)goal[:\s]+(.+?)(?:\n|$)',
        r'(?i)we need to\s+(.+?)(?:\n|$)',
        r'(?i)working on\s+(.+?)(?:\n|$)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    
    return "[Intent not explicitly stated]"

def extract_outcomes(text: str) -> list:
    """Extract completed work / outcomes."""
    outcomes = []
    
    # Look for completion markers
    patterns = [
        r'(?i)(?:completed?|finished|done)[:\s]+(.+?)(?:\n|$)',
        r'(?i)✅\s*(.+?)(?:\n|$)',
        r'(?i)outcome[:\s]+(.+?)(?:\n|$)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        outcomes.extend([m.strip() for m in matches])
    
    return outcomes or ["[No explicit outcomes recorded]"]

def extract_blockers(text: str) -> list:
    """Extract blockers / stuck points."""
    blockers = []
    
    patterns = [
        r'(?i)(?:blocker|stuck|blocked by)[:\s]+(.+?)(?:\n|$)',
        r'(?i)❌\s*(.+?)(?:\n|$)',
        r'(?i)need help with[:\s]+(.+?)(?:\n|$)',
        r'(?i)unclear[:\s]+(.+?)(?:\n|$)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        blockers.extend([m.strip() for m in matches])
    
    return blockers or []

def extract_next_steps(text: str) -> list:
    """Extract proposed next steps."""
    steps = []
    
    patterns = [
        r'(?i)(?:next|todo|upcoming)[:\s]+(.+?)(?:\n|$)',
        r'(?i)→\s*(.+?)(?:\n|$)',
        r'(?i)proposed[:\s]+(.+?)(?:\n|$)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        steps.extend([m.strip() for m in matches])
    
    return steps or ["[No explicit next steps]"]

def generate_tldr(project_path: str, output_path: str = None) -> str:
    """Generate TLDR from session artifacts."""
    artifacts = read_session_artifacts(project_path)
    
    if not artifacts['status'] and not artifacts['review']:
        return "# TLDR\n\nNo session artifacts found.\n"
    
    # Combine all text for analysis
    all_text = "\n".join(filter(None, [artifacts['status'], artifacts['review']]))
    
    tldr = f"""# TLDR - {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Intent
{extract_intent(all_text)}

## Outcomes
{chr(10).join(['- ' + o for o in extract_outcomes(all_text)])}

## Blockers
{chr(10).join(['- ' + b for b in extract_blockers(all_text)]) if extract_blockers(all_text) else "- None recorded"}

## Next Steps
{chr(10).join(['- ' + s for s in extract_next_steps(all_text)])}

---
*Generated from session artifacts*
"""
    
    # Write to file if path provided
    if output_path:
        Path(output_path).write_text(tldr)
    
    return tldr

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: tldr-update.py <project_path> [output_path]")
        sys.exit(1)
    
    project_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(generate_tldr(project_path, output_path))
