#!/usr/bin/env node
/**
 * Python Bridge - Executes Python scripts and returns parsed JSON output
 */

import { spawn, execSync } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Path to the attention-repo scripts directory (go up 2 levels from src/)
const SCRIPTS_DIR = join(__dirname, '..', '..', 'scripts');
const JIT_CONTEXT = join(SCRIPTS_DIR, 'jit-context.py');

// Prefer PATH for portability; explicit paths are fallbacks only.
const PYTHON_PATHS = [
  'python3',
  '/usr/bin/python3',
  '/usr/local/bin/python3',
  '/opt/homebrew/bin/python3'
];
const DEBUG_ENABLED = process.env.ATTENTION_REPO_DEBUG === '1';

function debugLog(event, fields = {}) {
  if (DEBUG_ENABLED) {
    console.error(JSON.stringify({ component: 'python-bridge', event, ...fields }));
  }
}

/**
 * Find working python executable - synchronous version
 */
function findPython() {
  for (const py of PYTHON_PATHS) {
    try {
      execSync(`${py} --version`, { stdio: 'ignore' });
      return py;
    } catch (e) {
      // Try next one
    }
  }
  return 'python3'; // fallback
}

// Initialize python path once
const pythonPath = findPython();
debugLog('python_selected', { pythonPath });

/**
 * Execute a Python script with arguments and return parsed JSON output.
 * Commands that intentionally emit prose must pass { allowRaw: true } explicitly.
 * @param {string[]} args - Arguments to pass to the Python script
 * @param {{allowRaw?: boolean}} options
 * @returns {Promise<object>} - Parsed JSON output or { raw } when allowRaw is true
 */
export function execPython(args, options = {}) {
  return new Promise((resolve, reject) => {
    const proc = spawn(pythonPath, [JIT_CONTEXT, ...args], {
      cwd: SCRIPTS_DIR,
      env: { 
        ...process.env,
        PATH: '/usr/local/bin:/usr/bin:/opt/homebrew/bin:' + (process.env.PATH || '')
      },
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    proc.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    proc.on('close', (code) => {
      debugLog('python_exit', { code, args });
      if (code !== 0) {
        reject(new Error(`Python script exited with code ${code}: ${stderr || stdout || '(no output)'}`));
        return;
      }

      const trimmed = stdout.trim();
      try {
        resolve(JSON.parse(trimmed));
        return;
      } catch {
        // Fall through to anchored object extraction for commands that log around JSON.
      }

      const jsonMatch = trimmed.match(/^([\s\S]*?)(\{[\s\S]*\})([\s\S]*?)$/);
      if (jsonMatch) {
        try {
          resolve(JSON.parse(jsonMatch[2]));
          return;
        } catch {
          // Fall through to raw/error handling below.
        }
      }

      if (options.allowRaw) {
        resolve({ raw: stdout });
        return;
      }

      reject(new Error(`Python command produced non-JSON output: ${stdout || '(no output)'}`));
    });

    proc.on('error', (err) => {
      reject(err);
    });
  });
}

/**
 * Get the repo path - from env or default to workspace
 */
export function getRepoPath(repoPath) {
  return repoPath || process.env.ATTENTION_REPO_PATH || process.cwd();
}

export default { execPython, getRepoPath, JIT_CONTEXT, SCRIPTS_DIR };
