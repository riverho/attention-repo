# Attention Repo

*Deployment intelligence for coding agents.*

Version: v0.4.1. 
Update Date: 23 March 2026 
Status: public package, source-visible implementation repo, not a full open-source release yet.

> [!WARNING]
> Attention Repo is currently under private testing. Expect rough edges, incomplete workflows, breaking changes between versions, and occasional buggy behavior. You are responsible for validating the package in your own environment, verifying repository boundaries before acting on them, and reviewing any output before using it in production or compliance-sensitive workflows.

> [!IMPORTANT]
> Officially supported operating systems today are macOS and Linux. Native Windows usage is not currently supported as a first-class path. If you are on Windows, use WSL2 or a Linux Docker container.

Attention Repo helps humans and coding agents answer a simple question before editing code:

**What deployable surface am I touching, and what boundary am I about to cross?**

Agents can already read files, trace symbols, edit code, and run tests. They still miss repo-level reality:

- one folder may deploy through a different pipeline than the next
- a small edit may cross into another service
- a task may be in scope for one entity and out of scope for another
- post-change review often happens after the boundary mistake has already happened

Attention Repo adds repo and deployment awareness on top of the agent you already use.

---

## Why It Exists

Without boundary intelligence, coding agents often make the same class of mistakes:

- edit the wrong service
- assume the wrong CI/CD pipeline
- widen scope silently
- produce low-auditability changes

Attention Repo is built to reduce that failure mode.

It is not another planner. It is a boundary-aware layer that helps humans and agents work inside the intended deployable surface.

---

## What You Get

Today, the package gives you:

- a local CLI: `attention-repo`
- a local MCP server: `attention-repo mcp`
- a shared tool registry for agent hosts
- a workflow for declaring scope, assembling context, validating changes, and finalizing audits

The current MCP surface includes:

1. `attention_resolve_scope`
2. `attention_get_constraints`
3. `attention_declare_scope`
4. `attention_assemble_context`
5. `attention_validate_changes`
6. `attention_finalize_audit`

You can inspect the locally shipped registry with:

```bash
attention-repo tools
attention-repo tools --json
```

---

## Install

The current public install surface is one package:

```bash
bun install -g @summon-ai/attention-repo
```

Then configure your local key and verify the install:

```bash
attention-repo setup --key "ak_attention_repo_xxx"
attention-repo status
```

Expected next-step commands:

```bash
attention-repo tools
attention-repo mcp-config
attention-repo mcp-config codex
```

---

## Platform Support

Attention Repo is currently intended for:

- macOS
- Linux

Not currently first-class:

- Windows native (`cmd.exe`, PowerShell, or Git Bash without a Linux layer)

Windows users should prefer one of the Linux-backed paths below.

### Windows with WSL2

WSL2 is the recommended Windows setup.

1. Install WSL2 with Ubuntu or another Linux distribution.
2. Install Bun, Node.js 18+, Python 3, and Git inside the Linux environment.
3. Clone or mount your repo inside the Linux filesystem when possible.
4. Install the package:

```bash
bun install -g @summon-ai/attention-repo
```

5. Verify the install:

```bash
attention-repo status
attention-repo mcp-config codex
```

### Windows with Docker

Docker is a fallback path, not an officially supported host workflow.

If you cannot use WSL2, run Attention Repo inside a Linux container that has Bun, Node.js, Python 3, and Git available. A minimal example is:

```bash
docker run --rm -it \
  -v "$PWD":/workspace \
  -w /workspace \
  ubuntu:24.04 bash

apt-get update
apt-get install -y curl unzip git python3 ca-certificates
curl -fsSL https://bun.sh/install | bash
export PATH="$HOME/.bun/bin:$PATH"

bun install -g @summon-ai/attention-repo
attention-repo status
attention-repo mcp-config codex
```

Notes:

- container state is ephemeral unless you persist it deliberately
- MCP usage still depends on mounting the target repository into the container
- Docker is best treated as an experimental compatibility path

---

## Connect MCP

Attention Repo is designed to be consumed by an agent host over MCP.

Print a ready-to-paste JSON config:

```bash
attention-repo mcp-config
```

Print a Codex config snippet:

```bash
attention-repo mcp-config codex
```

The config shape is:

```json
{
  "mcpServers": {
    "attention-repo": {
      "command": "attention-repo",
      "args": ["mcp"]
    }
  }
}
```

To pin a specific repository path instead of using the adaptive default:

```bash
attention-repo mcp-config codex --repo /path/to/repo
```

Or start the MCP server directly:

```bash
attention-repo mcp
```

---

## What To Do After Install

### Human workflow

If your repo does not already have an Attention Repo map, initialize it:

```bash
attention-repo init .
```

Before editing behavior, declare the intended boundary:

```bash
attention-repo declare-intent . \
  --affected-entities E-ATTN-BIN-01 \
  --deployment-pipeline .github/workflows/ci.yml \
  --first-principle-summary "Improve packaged CLI output for operator setup flow." \
  --requires-new-entity false
```

Assemble scoped context:

```bash
attention-repo assemble .
```

Finalize with test evidence:

```bash
attention-repo finalize-change . \
  --tests-command "node tests/test_bun_cli.js" \
  --tests-result pass \
  --notes "CLI output updated and verified"
```

### Agent workflow

Once MCP is connected, the normal flow is:

1. `attention_resolve_scope`
2. `attention_get_constraints`
3. `attention_declare_scope`
4. `attention_assemble_context`
5. edit code
6. `attention_validate_changes`
7. `attention_finalize_audit`

Example MCP call shape:

```json
{
  "name": "attention_resolve_scope",
  "arguments": {
    "files": ["bin/attention-repo.js"]
  }
}
```

Example scope declaration:

```json
{
  "name": "attention_declare_scope",
  "arguments": {
    "entities": ["E-ATTN-BIN-01"],
    "pipelines": [".github/workflows/ci.yml"],
    "summary": "Improve packaged CLI output for operator setup flow",
    "requiresNewEntity": false
  }
}
```

The goal is simple: the human and the agent should agree on the deployable boundary before edits begin.

---

## Who It Is For

Attention Repo fits teams that:

- already use coding agents
- work in repos with multiple deployable surfaces
- care about CI/CD ownership and auditability
- want agents to stay inside declared boundaries

It is less useful for:

- toy single-service repos
- teams not using coding agents
- teams looking for a broad governance platform instead of a focused boundary tool

---

## Workflow Guide

Attention Repo supports two practical modes today.

### MCP-first agent workflow

This is the main public-facing usage pattern:

1. install the package
2. connect `attention-repo mcp`
3. let the agent use the MCP tool sequence:
   - `attention_resolve_scope`
   - `attention_get_constraints`
   - `attention_declare_scope`
   - `attention_assemble_context`
   - `attention_validate_changes`
   - `attention_finalize_audit`

### Strict operator workflow

This is the local CLI workflow for humans who want explicit gates and status updates.

```bash
attention-repo declare-intent /path/to/repo \
  --affected-entities E-AUTH-01 \
  --deployment-pipeline .github/workflows/api.yml \
  --first-principle-summary "Validate JWT signature and emit auth verdict." \
  --requires-new-entity false

attention-repo assemble /path/to/repo

attention-repo update-task /path/to/repo \
  --status-markdown "Mapped entities and started auth middleware edits."

attention-repo finalize-change /path/to/repo \
  --tests-command "python3 -m unittest discover -s tests -p 'test_*.py'" \
  --tests-result pass \
  --notes "Auth boundary preserved"
```

### Common commands

Initialize a repo:

```bash
attention-repo init .
```

Start local focus:

```bash
attention-repo start .
attention-repo start . "Fix auth token validation in middleware."
```

Wrap up and release attention state:

```bash
attention-repo wrap .
attention-repo release-attention . --note "Task complete"
```

Rebuild local index and state:

```bash
attention-repo reindex
attention-repo repair
```

Canonical version metadata lives in [version.json](./version.json).

---

## License and Usage Restrictions

This project is released as `UNLICENSED`.

All rights are reserved. No permission is granted to copy, reproduce, modify, redistribute, sublicense, publish, or use this material except with explicit written authorization from the creator.

Source-visible access does not grant open-source rights.

Created by River Ho @ NMC.

Copyright 2026 River Ho @ NMC. All rights reserved.
