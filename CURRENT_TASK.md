<!-- Last synced: 2026-03-09T04:19:49.803292+00:00 | Version: 0.3.0 -->
# CURRENT_TASK.md

## Status
Simplified the attention-layer user surface to `start <project>`, `init`, and `wrap <project>`, aligned Telegram buttons to `Projects | Index New | Wrap Up`, added a real terminal `wrap` command, and kept the central control plane under ~/.openclaw/attention-layer as the source of truth for project indexing.

## Planning
- Attention session roadmap documented in `docs/ATTENTION_SESSION_PLAN.md`

## Architectural Intent
- Entities: E-ATTN-PLUGIN-01
- Pipeline: .github/workflows/ci.yml
- First Principle: Expose a minimal, memorable workflow across Telegram and text channels while keeping project memory repo-local and cross-project indexing centralized.
- Requires New Entity: False

## Updated
2026-03-09T02:00:00+08:00
