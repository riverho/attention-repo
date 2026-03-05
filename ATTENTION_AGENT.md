# Attention Layer Redesign (Lean v3)

This repository no longer runs a background attention agent.

## Enforced model
- First-principles reasoning is mandatory.
- Architectural intent declaration is mandatory before edits.
- Entity IDs must exist in `!MAP.md`.
- Deployment pipeline must exist on disk.

## Entry points
- `scripts/attention declare-intent ...`
- `scripts/attention assemble ...`
- `scripts/attention finalize-change ...`

The attention layer is now just-in-time and deterministic.
