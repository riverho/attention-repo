# Summon Bridge — Calling Agents from OpenClaw

## When to Spawn

Spawn subagents when:
1. Task is parallelizable (can run while you do other work)
2. Task needs isolation (don't pollute main session context)
3. Task is self-contained (clear input → clear output)
4. Human explicitly asked for "background work"

Don't spawn when:
1. Human wants real-time conversation
2. Task needs clarification mid-stream
3. Human prefers direct interaction

## Spawning Pattern

```javascript
// Three-layer funnel for complex tasks

// Layer 1: Search
sessions_spawn({
  agentId: "codex",
  task: `Search codebase for files related to: ${intent}.
         Return 10-20 candidates with relevance notes.
         Be aggressive in filtering — discard 90%.`,
  mode: "run"
})

// Layer 2: Plan (depends on Layer 1 output)
sessions_spawn({
  agentId: "claude", 
  task: `Given these candidates [${candidates}], 
         analyze dependencies and identify 3-5 leverage points.`,
  mode: "run"
})

// Layer 3: Synthesize (depends on Layer 2 output)
sessions_spawn({
  agentId: "claude",
  task: `Read !MAP.md and !CONNECTIONS.md.
         Given this plan [${plan}], synthesize 3 options.
         Wait for human choice before proceeding.`,
  mode: "run"
})
```

## Reading Results

Agents write artifacts that you read:

```
~/.summon/state/agent-sessions.json  → Track running sessions
./STATUS.md                           → Agent's findings
./REVIEW.md                           → Proposals for human
./TLDR.md                             → Compressed state
```

## Coordination

Track state in `~/.summon/state/`:

```json
{
  "queryId": "uuid",
  "intent": "implement auth flow",
  "layer1": {"status": "completed", "output": "..."},
  "layer2": {"status": "running", "output": null},
  "layer3": {"status": "waiting", "output": null},
  "humanGate": "pending"
}
```

## Error Handling

- If agent fails → Log to !CONNECTIONS.md Uncertainty section
- If output unclear → Ask human, don't guess
- If timeout → Report partial results, suggest retry

## Transparency Requirements

Always tell human:
1. What agents were spawned
2. What layer they're in
3. When they complete
4. What the output means (in non-technical terms)
