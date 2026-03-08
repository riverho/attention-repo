# Root Cause: `!MAP.md` Staleness

## Incident Context
- Repo: `summon-A2A-academy`
- Date: 2026-03-06
- Symptom: `!MAP.md` remained partially stale after canonical flow shifted to Factory `/api/session` authority.

## Root Cause
1. **Process gap in Lean v3 workflow**  
`declare-intent -> assemble -> implement -> finalize` does not explicitly require a post-change `!MAP.md` freshness check.

2. **Entity drift without metadata refresh**  
Work changed endpoint semantics (legacy route became compatibility shim), but entity `endpoint/description` fields were not updated in the same change set.

3. **Runtime truth split**  
Attention lifecycle validated repo edits and tests, but deployment/runtime validation happened later; by then docs-map drift was already present.

## Contributing Factors
- `!MAP.md` treated as mostly static registry instead of living architecture contract.
- No deterministic gate that fails finalize when declared entities materially changed behavior but mapping text did not.

## Required Adjustment (Skill Origin)
1. Add mandatory **Map Freshness Check** before `finalize-change`.
2. If endpoint ownership/behavior changed, require either:
- `!MAP.md` update for affected entity metadata, or
- explicit `CURRENT_TASK.md` note: `"map-no-change-justification: ..."` with rationale.
3. Extend finalize notes template to include:
- `map_freshness: updated | verified-no-change`
- `affected_entity_deltas: ...`

## Proposed Lean v3.1 Workflow
1. `declare-intent`
2. `assemble`
3. implement edits/tests
4. optional `register-new-entity`
5. `update-task`
6. **map-freshness-check (new)**
7. `finalize-change`

## Definition of Current
`!MAP.md` is current when, for each affected entity:
- `endpoint` reflects real runtime role (canonical vs compatibility shim),
- `file_path` matches active implementation location,
- `description` matches present responsibility boundaries,
- `ci_cd` mapping still points to real deployment pipeline.
