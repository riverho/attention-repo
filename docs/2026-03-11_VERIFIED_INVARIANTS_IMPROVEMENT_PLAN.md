# Verified Invariants Improvement Plan

Date: 2026-03-11
Source repo: `summon-A2A-academy`

## Learning Of Today

The highest-value improvement for `attention-repo` is not more memory. It is a first-class `verified invariants` layer that is separate from general notes, plans, and WIP summaries.

The core failure pattern observed today was not missing information. It was stale assumptions mixing with true statements:

- a tunnel host existed, but the real callback contract required the full `/hooks/agent` path
- `gateway.auth.token` existed, but the real callback auth source was `hooks.token`
- `~/.summon-academy` existed, but it was not the runtime truth for the webhook listener
- Cloudflare secrets existed, but their alignment across Pages, Factory, and local runtime still had to be proven

These are not ordinary notes. They are operational invariants. When they drift, debugging time explodes.

## Improvement Goal

Add a dedicated `verified invariants` surface so proven truths are stored, re-checked, and expired deliberately instead of being buried inside status prose.

## Proposed Invariant Record Shape

Each invariant should have:

- `statement`
- `scope`
- `status`
- `last_verified_at`
- `verification_method`
- `verification_evidence`
- `depends_on`
- `owner`
- `expiry_rule`
- `supersedes`

Example statements:

- canonical training flow is `start -> sessions -> rate -> decision`
- callback URL must include `/hooks/agent`
- local callback auth source is `~/.openclaw/openclaw.json` `hooks.token`
- `~/.summon-academy` is not callback runtime truth
- Factory and Pages must share `OPENCLAW_WEBHOOK_TOKEN`

## Why This Matters

This would change `attention-repo` from a strong memory system into a stronger anti-drift system.

The operational win is:

- proven truths become explicit and queryable
- stale assumptions can expire automatically
- wrap/finalize can warn when a change touches an invariant without re-verifying it
- agents stop re-opening already-closed questions unless evidence says they should

## Suggested Product Changes

1. Add a repo-local file such as `.attention/verified_invariants.json`.
2. Add a central projection in the attention control plane so cross-repo state can surface verified invariants separately from WIP.
3. Add CLI support:
   - `attention verify-invariant`
   - `attention list-invariants`
   - `attention expire-invariants`
4. Add finalize checks that fail soft when affected invariants have no fresh verification.
5. Add wrap output that highlights:
   - newly proven invariants
   - stale invariants
   - assumptions still unverified

## Immediate Next Step

Prototype the invariant schema and one CLI path in the `attention-repo` skill itself before expanding it across other repos.
