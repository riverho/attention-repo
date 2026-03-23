/**
 * Attention Repo MCP Server - Cloudflare Worker
 * 
 * HTTP-based MCP server for CI/CD entity mapping.
 * Deploy with: wrangler deploy
 */

import { callTool, toolDefinitions } from './tools.js';

// JSON-RPC request handler
async function handleMcpRequest(request) {
  try {
    const body = await request.json();
    const { jsonrpc, id, method, params } = body;

    if (jsonrpc !== '2.0') {
      return jsonRpcError(id, -32600, 'Invalid JSON-RPC version');
    }

    // Handle methods
    switch (method) {
      case 'tools/list':
        return jsonRpcResponse(id, { tools: toolDefinitions });

      case 'resources/list':
        return jsonRpcResponse(id, { resources: [] });

      case 'resources/templates/list':
        return jsonRpcResponse(id, { resourceTemplates: [] });

      case 'tools/call': {
        const { name, arguments: args } = params;
        
        const result = await callTool(name, args);

        return jsonRpcResponse(id, {
          content: [{
            type: 'text',
            text: typeof result === 'string' ? result : JSON.stringify(result, null, 2)
          }]
        });
      }

      case 'initialize':
        return jsonRpcResponse(id, {
          protocolVersion: '2024-11-05',
          capabilities: { resources: {}, tools: {} },
          serverInfo: { name: 'attention-repo', version: '0.1.0' }
        });

      default:
        return jsonRpcError(id, -32601, `Unknown method: ${method}`);
    }
  } catch (error) {
    return jsonRpcError(null, -32603, error.message);
  }
}

function jsonRpcResponse(id, result) {
  return new Response(JSON.stringify({ jsonrpc: '2.0', id, result }), {
    headers: { 'Content-Type': 'application/json' }
  });
}

function jsonRpcError(id, code, message) {
  return new Response(JSON.stringify({ 
    jsonrpc: '2.0', 
    id, 
    error: { code, message } 
  }), {
    status: code === -32601 ? 404 : 400,
    headers: { 'Content-Type': 'application/json' }
  });
}

// CORS headers
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export default {
  async fetch(request, env) {
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405, headers: corsHeaders });
    }

    const response = await handleMcpRequest(request);
    
    // Add CORS to response
    const newHeaders = new Headers(response.headers);
    for (const [key, value] of Object.entries(corsHeaders)) {
      newHeaders.set(key, value);
    }
    
    return new Response(response.body, {
      status: response.status,
      headers: newHeaders
    });
  }
};
