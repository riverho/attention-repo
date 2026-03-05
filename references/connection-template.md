# !CONNECTIONS.md Template

Copy this to your project's `docs/` folder and customize.

---

```markdown
# !CONNECTIONS.md — How [AI Name] Maps Your Context

*This file is written by [AI], read by both of us. It shows how your anchors connect in my attention space.*

---

## Current Scope

**Active Intent:** [What we're working on right now — 1 sentence]

**Mood/Tone:** [How the work felt last session — e.g., "focused but scattered", "blocked on auth", "making progress"]

**Blockers:** [What paused progress — specific files, decisions, or dependencies]

---

## Anchor Map

*Your notes and how I see them connecting*

| Anchor | Type | Connects To | Why It Resonates |
|--------|------|-------------|------------------|
| `!MAP.md` | Gate | All sessions | Source of truth — read first every time |
| `[example.md]` | Decision | [implementation/] | Core architectural choice documented |
| `[todo.md]` | Log | [active tasks] | Running list, frequently updated |
| `[meeting-2024-02-26.md]` | Log | [decisions/] | Raw notes, being distilled |

---

## Attention Paths

*How I traverse when you ask for help*

```
When you say: "Continue the auth flow"
I read:     !MAP.md → docs/auth/ → last session notes
I propose:  2-3 implementation options
You pick:   Direction or refine requirements
```

```
When you say: "What's the status?"
I read:     !MAP.md → TLDR.md → recent commits
I tell:     Current state, blockers, next steps
```

---

## Discards

*What I filtered out this session — transparency log*

- `old-api-spec.md` — outdated, newer version in docs/api/v2/
- `experiment-2024/` — archived, no current relevance per !MAP.md
- `node_modules/` — build artifact, not source
- 3 files matching "auth" that don't affect implementation path

---

## Uncertainty Log

*Where I'm fuzzy — needs your input*

- "Should auth flow include mobile?" — not specified in !MAP.md
- "Timeline priority?" — unclear if this is urgent or exploratory
- "Tech stack preference?" — see multiple patterns in codebase

---

## Session History

| Date | Focus | Outcome | Mood |
|------|-------|---------|------|
| 2024-02-26 | Auth flow design | 3 options proposed | Blocked on decision |
| 2024-02-25 | Architecture review | Patterns documented | Clear |

---

*Last updated: YYYY-MM-DD HH:MM by [AI]*
*Next: Your turn to correct, expand, or redirect*
```

---

## How to Use This Template

1. **Copy** to `docs/!CONNECTIONS.md`
2. **Customize** the header with your AI's name
3. **Fill** Current Scope at start of each session
4. **Update** Anchor Map as notes change
5. **Log** Discards every session — transparency
6. **Ask** about Uncertainties — don't guess
7. **Append** to Session History weekly

## Co-Editing Guidelines

**AI writes:**
- Discards (what I filtered)
- Attention Paths (how I traverse)
- Last updated timestamp

**Human writes:**
- Active Intent (what you want)
- Blockers (what's stuck)
- Uncertainty answers (clarify my questions)

**Both edit:**
- Anchor Map (add/remove connections)
- Session History (both perspectives)

## When to Update

- **Start of session:** Check Current Scope, answer Uncertainties
- **During session:** Log Discards as they happen
- **End of session:** Update Session History, set next Active Intent
