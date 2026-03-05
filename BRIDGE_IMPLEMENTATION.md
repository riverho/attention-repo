# Bridge Implementation (Lean v3)

The markdown-memory bridge from v1 is removed.

## Current bridge model
Runtime context is assembled only after a validated architectural declaration.

Inputs:
- `!MAP.md` (entity registry + architecture)
- `CURRENT_TASK.md` (ephemeral task status)
- `git status -s`
- `git log -1 --stat`
- Injected CI/CD files mapped from selected entities

Use `scripts/attention` for all lifecycle operations.
