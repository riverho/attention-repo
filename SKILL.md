---
name: attention-layer
description: First-principles, CI/CD-entity aware attention layer with mandatory architectural intent declaration.
---

# Attention Layer (Lean v3)

## Objective
Force a strict OODA loop where code edits are gated by architectural intent and CI/CD mapping.

## Rules
1. You are a Staff Infrastructure Engineer.
2. Before code changes, you must call `declare-intent`.
3. Entity IDs must come from `!MAP.md`.
4. Deployment pipeline must exist on disk.
5. If architecture changes, register a new entity explicitly.

## Commands
```bash
scripts/attention init <repo>

scripts/attention declare-intent <repo> \
  --affected-entities E-AUTH-01 \
  --deployment-pipeline .github/workflows/api.yml \
  --first-principle-summary "Validates JWT against secret and returns auth verdict." \
  --requires-new-entity false

scripts/attention assemble <repo>
scripts/attention update-task <repo> --status-markdown "Mapped entities; editing auth middleware."
scripts/attention register-new-entity <repo> --id E-STRIPE-HOOK --type Webhook --file-path src/api/stripe-webhook.ts --ci-cd .github/workflows/deploy-workers.yml --endpoint "POST /webhook/stripe" --description "Stripe subscription webhook"
scripts/attention finalize-change <repo> --tests-command "npm test" --tests-result pass --notes "Ready for review"
scripts/attention clear-task <repo>
```

## Workflow
1. `declare-intent`
2. `assemble`
3. implement edits/tests
4. optional `register-new-entity`
5. `update-task`
6. `finalize-change`

## Maturity Rubric
- L1 Prototype: ad hoc prompts, no entity mapping.
- L2 Structured: declaration gate + entity registry.
- L3 Operational: CI/CD injection + finalize reports.
- L4 Production-ready: enforced in orchestration runtime, protected CI, deployment checks.

This repository now implements L3.
