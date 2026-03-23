# Attention Repo MCP Server

MCP (Model Context Protocol) server that exposes Attention Repo functionality to AI coding agents like Claude Code, Cursor, and Windsurf.

Canonical contract reference:

- [docs/MASTER_SPEC_HANDOFF.md](/Users/river/.openclaw/workspace/projects/attention-repo/docs/MASTER_SPEC_HANDOFF.md)
- [/Users/river/.openclaw/workspace/notes/attention-repo/MASTER_DESIGN_AND_IMPLEMENTATION.md](/Users/river/.openclaw/workspace/notes/attention-repo/MASTER_DESIGN_AND_IMPLEMENTATION.md)

This README describes the implementation state in this repo.
The master design doc defines the target launch contract.

## Installation

The official user-facing install surface is the root package:

```bash
bun install -g @summon-ai/attention-repo
attention-repo setup --key "ak_attention_repo_xxx"
attention-repo status
```

To print a ready-to-paste MCP config snippet:

```bash
attention-repo mcp-config
attention-repo mcp-config codex
```

This `mcp-server/` package is kept for local development inside the repo.
It is not the public release artifact.

## Usage

### Standalone

```bash
# Set the repository path
export ATTENTION_REPO_PATH=/path/to/your/repo

# Run the server
node index.js
```

### Packaged target

```json
{
  "mcpServers": {
    "attention-repo": {
      "command": "attention-repo",
      "args": ["mcp"],
      "env": {
        "ATTENTION_REPO_PATH": "."
      }
    }
  }
}
```

## Tools

### Current implementation

| Tool | Description |
|------|-------------|
| `attention_resolve_scope` | Resolve files or a task into entities, services, pipelines, and risks |
| `attention_get_constraints` | Return machine-readable in-scope and out-of-scope constraints |
| `attention_declare_scope` | Lock the intended boundary before edits begin |
| `attention_assemble_context` | Assemble scoped implementation context for the active declaration |
| `attention_validate_changes` | Compare changed files against the declared boundary |
| `attention_finalize_audit` | Produce factual audit output from the real change set |

### Target launch contract

The target MCP surface is v2:

- `attention_resolve_scope`
- `attention_get_constraints`
- `attention_declare_scope`
- `attention_assemble_context`
- `attention_validate_changes`
- `attention_finalize_audit`

Compatibility aliases for the older v1 names remain available temporarily:

- `attention_query`
- `attention_declare_intent`
- `attention_freshness`
- `attention_assemble`
- `attention_finalize`

## Configuration

Set `ATTENTION_REPO_PATH` environment variable to point to your repository:

```bash
export ATTENTION_REPO_PATH=~/my-project
```

## Development

```bash
# Install dependencies
npm install

# Run in development
npm start

# Show the packaged tool registry
node ../bin/attention-repo.js tools

# Print the packaged MCP config
node ../bin/attention-repo.js mcp-config

# Test a specific tool
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"attention_resolve_scope","arguments":{"files":["src/index.ts"]}}}' | node index.js
```

## Requirements

- Node.js >= 18
- Python 3
- Attention Repo scripts (jit-context.py) in ../scripts/
