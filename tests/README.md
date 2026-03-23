# Attention Repo - Test Suite

## Running Tests

```bash
# Run the local-core Python suite without extra dependencies
python3 -m unittest discover -s tests -p 'test_*.py' -v

# Optional: run with pytest if installed
python3 -m pytest tests/ -v

# Run the standalone local CLI smoke test
node tests/test_bun_cli.js

# Run the standalone MCP integration smoke test
node tests/test_mcp_integration.js
```

## Scope

The active OSS-local testing surface is:

- Bun CLI
- local MCP runtime
- local workflow behavior

Archived skill/OpenClaw/Telegram surfaces are out of scope for OSS-local testing.

## Test Structure

| File | Category | Tests | Status |
|------|----------|-------|--------|
| `test_gate_effectiveness.py` | Gate | 12 | 9 ✅, 3 ⏳ |
| `test_context_quality.py` | Context | 2 | 0 ✅, 2 ⏳ |
| `test_drift_detection.py` | Drift | 6 | 3 ✅, 3 ⏳ |
| `test_audit_chain.py` | Audit | 2 | 1 ✅, 1 ⏳ |
| `test_integration.py` | Integration | 5 | 0 ✅, 5 ⏳ |

**Total: 27 tests | Implemented: 13 | Pending: 14**

## Coverage Mapping

See `../notes/attention-repo/test-cases/` for detailed test case specifications.
