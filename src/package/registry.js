export const PRODUCT_ID = "attention-repo";
export const PRODUCT_DISPLAY_NAME = "Attention Repo";
export const PACKAGE_NAME = "@summon-ai/attention-repo";
export const MCP_SERVER_NAME = "attention-repo";
export const MCP_COMMAND = "attention-repo";
export const MCP_ARGS = Object.freeze(["mcp"]);

export const OFFICIAL_MCP_TOOLS = Object.freeze([
  {
    name: "attention_resolve_scope",
    description: "Resolve files or a task into entities, services, pipelines, and risks.",
    stability: "official",
  },
  {
    name: "attention_get_constraints",
    description: "Return machine-readable in-scope and out-of-scope constraints for the active scope.",
    stability: "official",
  },
  {
    name: "attention_declare_scope",
    description: "Lock the intended boundary before edits begin.",
    stability: "official",
  },
  {
    name: "attention_assemble_context",
    description: "Assemble scoped implementation context tied to the active declaration.",
    stability: "official",
  },
  {
    name: "attention_validate_changes",
    description: "Compare changed files against the declared boundary.",
    stability: "official",
  },
  {
    name: "attention_finalize_audit",
    description: "Produce factual audit output from the real change set.",
    stability: "official",
  },
]);

export const LEGACY_MCP_ALIASES = Object.freeze([
  {
    name: "attention_query",
    description: "Deprecated alias for attention_resolve_scope on a single file.",
    stability: "legacy",
    aliasFor: "attention_resolve_scope",
  },
  {
    name: "attention_declare_intent",
    description: "Deprecated alias for attention_declare_scope.",
    stability: "legacy",
    aliasFor: "attention_declare_scope",
  },
  {
    name: "attention_freshness",
    description: "Legacy topology check retained for compatibility.",
    stability: "legacy",
  },
  {
    name: "attention_assemble",
    description: "Deprecated alias for attention_assemble_context.",
    stability: "legacy",
    aliasFor: "attention_assemble_context",
  },
  {
    name: "attention_finalize",
    description: "Deprecated alias for attention_finalize_audit.",
    stability: "legacy",
    aliasFor: "attention_finalize_audit",
  },
]);

const toolRegistry = [...OFFICIAL_MCP_TOOLS, ...LEGACY_MCP_ALIASES];
const toolLookup = new Map(toolRegistry.map((tool) => [tool.name, tool]));

export function getToolRegistry() {
  return toolRegistry.map((tool) => ({ ...tool }));
}

export function getToolMetadata(name) {
  return toolLookup.get(name) || null;
}

export function getDefaultMcpServerConfig(repoPath) {
  const serverConfig = {
    command: MCP_COMMAND,
    args: [...MCP_ARGS],
  };

  if (repoPath) {
    serverConfig.env = {
      ATTENTION_REPO_PATH: repoPath,
    };
  }

  return {
    mcpServers: {
      [MCP_SERVER_NAME]: serverConfig,
    },
  };
}

export function renderJsonMcpConfig(repoPath) {
  return JSON.stringify(getDefaultMcpServerConfig(repoPath), null, 2);
}

export function renderCodexMcpConfig(repoPath) {
  const lines = [
    `[mcp_servers."${MCP_SERVER_NAME}"]`,
    `command = "${MCP_COMMAND}"`,
    `args = ["${MCP_ARGS.join('", "')}"]`,
  ];

  if (repoPath) {
    lines.push(`env = { ATTENTION_REPO_PATH = "${repoPath}" }`);
  }

  return lines.join("\n");
}
