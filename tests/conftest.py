#!/usr/bin/env python3
"""
Attention Repo - Test Suite
===========================

Run all tests:
    python -m pytest tests/ -v

Run specific category:
    python -m pytest tests/test_gate_effectiveness.py -v
    python -m pytest tests/test_context_quality.py -v
    python -m pytest tests/test_drift_detection.py -v
    python -m pytest tests/test_audit_chain.py -v
    python -m pytest tests/test_integration.py -v

Test Coverage:
    - Gate Effectiveness: 12 tests (9 implemented, 3 pending)
    - Context Quality: 2 tests (0 implemented)
    - Drift Detection: 6 tests (3 implemented, 3 pending)
    - Audit Chain: 2 tests (1 implemented, 1 pending)
    - Integration: 5 tests (0 implemented)

Total: 27 tests
Implemented: 13
Pending: 14
"""

import sys
from pathlib import Path

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
