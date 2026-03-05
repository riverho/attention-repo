# Summon Integration (Lean v3)

Use one autonomous engineer session with an explicit declaration gate.

## Recommended sequence
1. `scripts/attention declare-intent <repo> ...`
2. `scripts/attention assemble <repo>`
3. Execute edits/tests in one session
4. Optional `register-new-entity` if architecture changes
5. `scripts/attention finalize-change <repo> ...`

This replaces Search->Plan->Synthesize chaining.
