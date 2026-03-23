#!/usr/bin/env node
/**
 * Attention Repo MCP Server
 * 
 * Exposes Attention Repo functionality to AI coding agents via MCP protocol.
 * 
 * Usage:
 *   npx attention-repo-mcp
 *   # or
 *   node index.js
 * 
 * Environment:
 *   ATTENTION_REPO_PATH - Path to the repository (defaults to cwd)
 */

import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListResourceTemplatesRequestSchema,
  ListResourcesRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

import { callTool, toolDefinitions } from './src/tools.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SERVER_NAME = 'attention-repo';
const SERVER_VERSION = JSON.parse(readFileSync(join(__dirname, '..', 'version.json'), 'utf-8')).version;
const DEBUG_ENABLED = process.env.ATTENTION_REPO_DEBUG === '1';

function debugLog(message) {
  if (DEBUG_ENABLED) {
    console.error(message);
  }
}

class AttentionRepoServer {
  constructor() {
    this.server = new Server(
      {
        name: SERVER_NAME,
        version: SERVER_VERSION,
      },
      {
        capabilities: {
          resources: {},
          tools: {},
        },
      }
    );

    this.setupHandlers();
  }

  setupHandlers() {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: toolDefinitions
      };
    });

    this.server.setRequestHandler(ListResourcesRequestSchema, async () => {
      return {
        resources: []
      };
    });

    this.server.setRequestHandler(ListResourceTemplatesRequestSchema, async () => {
      return {
        resourceTemplates: []
      };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        const result = await callTool(name, args);

        // Format response
        return {
          content: [
            {
              type: 'text',
              text: typeof result === 'string' ? result : JSON.stringify(result, null, 2)
            }
          ]
        };

      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                error: 'TOOL_ERROR',
                message: error.message
              })
            }
          ],
          isError: true
        };
      }
    });
  }

  async connect(transport) {
    await this.server.connect(transport);
  }
}

async function main() {
  const server = new AttentionRepoServer();
  const transport = new StdioServerTransport();
  
  await server.connect(transport);

  debugLog(`${SERVER_NAME} v${SERVER_VERSION} started`);
}

// Run the server
main().catch((error) => {
  console.error(`Server error: ${error.message}`);
  process.exit(1);
});
