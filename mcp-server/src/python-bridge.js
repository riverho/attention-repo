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

// Try multiple python paths
const PYTHON_PATHS = [
  '/usr/local/bin/python3',
  '/usr/bin/python3',
  '/opt/homebrew/bin/python3',
  'python3'
];
const DEBUG_ENABLED = process.env.ATTENTION_REPO_DEBUG === '1';

function debugLog(message) {
  if (DEBUG_ENABLED) {
    console.error(message);
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
debugLog(`[Python Bridge] Using Python: ${pythonPath}`);

/**
 * Execute a Python script with arguments and return parsed JSON output
 * @param {string[]} args - Arguments to pass to the Python script
 * @returns {Promise<object>} - Parsed JSON output
 */
export function execPython(args) {
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
      if (code !== 0) {
        reject(new Error(`Python script exited with code ${code}: ${stderr || stdout || '(no output)'}`));
        return;
      }
      
      // Try to parse JSON output
      try {
        // Find JSON in output (some commands print additional text)
        const jsonMatch = stdout.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          resolve(JSON.parse(jsonMatch[0]));
        } else {
          // For non-JSON output (like assemble), return the raw text
          resolve({ raw: stdout });
        }
      } catch (e) {
        // If not JSON, return the raw output
        resolve({ raw: stdout });
      }
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
