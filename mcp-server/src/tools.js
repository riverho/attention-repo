/**
 * MCP Tools - Attention Repo functionality exposed via MCP protocol.
 */

import { execFileSync } from 'child_process';
import { existsSync, readdirSync, readFileSync } from 'fs';
import { join } from 'path';

import { execPython, getRepoPath } from './python-bridge.js';
import { getToolMetadata } from '../../src/package/registry.js';

function loadEntityRegistry(repo) {
  const mapPath = join(repo, '!MAP.md');
  if (!existsSync(mapPath)) {
    throw new Error('No !MAP.md found in repository. Run attention init first.');
  }

  const mapContent = readFileSync(mapPath, 'utf-8');
  const registryMatch = mapContent.match(/<!-- ENTITY_REGISTRY_START -->\n([\s\S]*?)\n<!-- ENTITY_REGISTRY_END -->/);
  if (!registryMatch) {
    throw new Error('No entity registry found in !MAP.md');
  }

  return JSON.parse(registryMatch[1]).entities || [];
}

function getDeclaredScope(repo) {
  const declPath = join(repo, '.attention', 'architectural_intent.json');
  if (!existsSync(declPath)) {
    return null;
  }
  return JSON.parse(readFileSync(declPath, 'utf-8'));
}

function normalizeFilePath(file) {
  return String(file || '').replace(/^\//, '');
}

function matchesFilePattern(pattern, file) {
  const normalizedFile = normalizeFilePath(file);
  const regexPattern = pattern
    .replace(/\*\*/g, '.*')
    .replace(/\*/g, '[^/]*')
    .replace(/\./g, '\\.');
  const regex = new RegExp(`^${regexPattern}$`);
  return regex.test(normalizedFile);
}

function serviceNameFromEntity(entity) {
  return entity.id
    .replace(/^E-/, '')
    .replace(/-\d+$/, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function resolveFilesToEntities(registry, files) {
  const entities = new Map();
  const unknowns = [];

  for (const file of files) {
    const match = registry.find((entity) => entity.file_path && matchesFilePattern(entity.file_path, file));
    if (match) {
      entities.set(match.id, match);
    } else {
      unknowns.push(normalizeFilePath(file));
    }
  }

  return { entities: [...entities.values()], unknowns };
}

function buildScope(entities) {
  return {
    entities: entities.map((entity) => entity.id),
    pipelines: [...new Set(entities.map((entity) => entity.ci_cd).filter(Boolean))],
    services: [...new Set(entities.map(serviceNameFromEntity))],
  };
}

function getChangedFiles(repo) {
  try {
    const output = execFileSync('git', ['status', '--short'], {
      cwd: repo,
      encoding: 'utf-8',
      stdio: ['ignore', 'pipe', 'ignore'],
    });

    return output
      .split('\n')
      .filter((line) => line.trim())
      .map((line) => {
        const payload = line.slice(3).trim();
        if (payload.includes(' -> ')) {
          return payload.split(' -> ').pop();
        }
        return payload;
      });
  } catch {
    return [];
  }
}

function findLatestFinalizeArtifact(repo) {
  const attentionDir = join(repo, '.attention');
  if (!existsSync(attentionDir)) {
    return '.attention/ATTENTION_FINALIZE.md';
  }

  const latest = readdirSync(attentionDir)
    .filter((name) => name.startsWith('ATTENTION_FINALIZE'))
    .sort()
    .pop();

  return latest ? `.attention/${latest}` : '.attention/ATTENTION_FINALIZE.md';
}

async function declareIntentInternal({ repo, entities, pipeline, summary, requiresNewEntity = false }) {
  const words = String(summary || '').trim().split(/\s+/).filter(Boolean);
  if (words.length < 6) {
    return {
      error: 'INVALID_DECLARATION',
      message: 'summary must contain at least 6 words',
    };
  }

  const registry = loadEntityRegistry(repo);
  const registeredEntities = registry.map((entity) => entity.id);
  const unknown = entities.filter((entityId) => !registeredEntities.includes(entityId));
  if (unknown.length > 0) {
    return {
      error: 'UNKNOWN_ENTITY',
      message: `Unknown entity IDs: ${unknown.join(', ')}`,
    };
  }

  const entityPipelines = [...new Set(registry
    .filter((entity) => entities.includes(entity.id))
    .map((entity) => entity.ci_cd)
    .filter(Boolean))];
  if (entityPipelines.length > 0 && (entityPipelines.length > 1 || !entityPipelines.includes(pipeline))) {
    return {
      error: 'PIPELINE_MISMATCH',
      message: `Pipeline must match the selected entity mappings. Expected one of: ${entityPipelines.join(', ')}`,
    };
  }

  await execPython([
    'declare-intent',
    repo,
    '--affected-entities',
    entities.join(','),
    '--deployment-pipeline',
    pipeline,
    '--first-principle-summary',
    summary,
    '--requires-new-entity',
    requiresNewEntity ? 'true' : 'false',
    '--task-type',
    'code',
  ], { allowRaw: true });

  const declaration = getDeclaredScope(repo);
  return {
    status: 'accepted',
    declaration_id: declaration?.declared_at || '.attention/architectural_intent.json',
    intent_file: '.attention/architectural_intent.json',
    entities,
    pipeline,
    validated: true,
    requires_new_entity: requiresNewEntity,
  };
}

export async function attentionResolveScope({ repo_path, task = '', files = [] } = {}) {
  const repo = getRepoPath(repo_path);

  try {
    const registry = loadEntityRegistry(repo);
    const normalizedFiles = Array.isArray(files) ? files.map(normalizeFilePath).filter(Boolean) : [];
    let matchedEntities = [];
    let unknowns = [];

    if (normalizedFiles.length > 0) {
      const resolved = resolveFilesToEntities(registry, normalizedFiles);
      matchedEntities = resolved.entities;
      unknowns = resolved.unknowns;
    } else {
      const declaration = getDeclaredScope(repo);
      if (declaration?.affected_entities?.length) {
        matchedEntities = registry.filter((entity) => declaration.affected_entities.includes(entity.id));
      }
    }

    const scope = buildScope(matchedEntities);
    const risks = [];
    if (scope.pipelines.length > 1) {
      risks.push('Resolved scope spans multiple deployment pipelines.');
    }
    if (unknowns.length > 0) {
      risks.push('Some files do not match any registered entity.');
    }
    if (!scope.entities.length && task) {
      risks.push('Task-only scope resolution is not yet inferred from natural language.');
    }

    return {
      status: scope.entities.length > 0 ? 'resolved' : 'unresolved',
      scope,
      risks,
      unknowns,
      confidence: unknowns.length === 0 && scope.entities.length > 0 ? 'high' : scope.entities.length > 0 ? 'medium' : 'low',
    };
  } catch (error) {
    return {
      error: 'UNKNOWN_ENTITY',
      message: error.message,
    };
  }
}

export async function attentionGetConstraints({ repo_path, entities = [] } = {}) {
  const repo = getRepoPath(repo_path);

  try {
    const registry = loadEntityRegistry(repo);
    const declaration = getDeclaredScope(repo);
    const entityIds = entities.length > 0 ? entities : declaration?.affected_entities || [];
    if (entityIds.length === 0) {
      return {
        error: 'NO_SCOPE',
        message: 'No entities supplied and no declaration is active.',
      };
    }

    const selected = registry.filter((entity) => entityIds.includes(entity.id));
    const unselected = registry.filter((entity) => !entityIds.includes(entity.id));
    return {
      status: 'ok',
      in_scope_paths: selected.map((entity) => entity.file_path).filter(Boolean),
      out_of_scope_paths: unselected.map((entity) => entity.file_path).filter(Boolean),
      pipeline_ownership: selected.map((entity) => ({
        entity: entity.id,
        pipeline: entity.ci_cd || null,
      })),
      boundary_rules: [
        'Declare scope before editing code.',
        '!MAP.md is the authoritative topology source.',
        'Changes touching undeclared entities should be rejected or re-declared.',
      ],
      runtime_notes: [
        `repo_path: ${repo}`,
        `declaration_active: ${declaration ? 'yes' : 'no'}`,
      ],
    };
  } catch (error) {
    return {
      error: 'CONSTRAINTS_FAILED',
      message: error.message,
    };
  }
}

export async function attentionDeclareScope({ repo_path, entities = [], pipelines = [], pipeline, summary, requiresNewEntity = false } = {}) {
  const repo = getRepoPath(repo_path);
  const acceptedPipeline = pipeline || pipelines[0];
  if (!acceptedPipeline) {
    return {
      error: 'INVALID_DECLARATION',
      message: 'pipeline or pipelines[0] is required',
    };
  }

  const result = await declareIntentInternal({
    repo,
    entities,
    pipeline: acceptedPipeline,
    summary,
    requiresNewEntity,
  });

  if (result.error) {
    return result;
  }

  return {
    declaration_id: result.declaration_id,
    accepted_entities: entities,
    accepted_pipelines: [acceptedPipeline],
    warnings: pipelines.length > 1 ? ['Only the first pipeline is currently enforced by the Python engine.'] : [],
  };
}

export async function attentionAssembleContext({ repo_path, declarationId, entities = [] } = {}) {
  const repo = getRepoPath(repo_path);

  try {
    const declaration = getDeclaredScope(repo);
    if (!declaration) {
      return {
        error: 'NO_DECLARATION',
        message: 'No scope declared. Run attention_declare_scope first.',
      };
    }

    const registry = loadEntityRegistry(repo);
    const entityIds = entities.length > 0 ? entities : declaration.affected_entities || [];
    const selected = registry.filter((entity) => entityIds.includes(entity.id));
    const result = await execPython(['assemble', repo], { allowRaw: true });
    const promptSummary = result.raw ? result.raw.trim() : JSON.stringify(result, null, 2);

    return {
      declaration_id: declarationId || declaration.declared_at || '.attention/architectural_intent.json',
      scope: buildScope(selected),
      files_in_scope: selected.map((entity) => entity.file_path).filter(Boolean),
      pipeline_files: [...new Set(selected.map((entity) => entity.ci_cd).filter(Boolean))],
      prompt_summary: promptSummary,
    };
  } catch (error) {
    return {
      error: 'ASSEMBLE_FAILED',
      message: error.message,
    };
  }
}

export async function attentionValidateChanges({ repo_path, files = [] } = {}) {
  const repo = getRepoPath(repo_path);

  try {
    const declaration = getDeclaredScope(repo);
    if (!declaration) {
      return {
        error: 'NO_DECLARATION',
        message: 'No scope declared. Run attention_declare_scope first.',
      };
    }

    const registry = loadEntityRegistry(repo);
    const changedFiles = Array.isArray(files) && files.length > 0 ? files.map(normalizeFilePath) : getChangedFiles(repo);
    const resolved = resolveFilesToEntities(registry, changedFiles);
    const declaredEntities = declaration.affected_entities || [];
    const undeclaredEntities = resolved.entities
      .map((entity) => entity.id)
      .filter((entityId) => !declaredEntities.includes(entityId));
    const outOfScopePaths = changedFiles.filter((file) => {
      return !registry.some((entity) => declaredEntities.includes(entity.id) && entity.file_path && matchesFilePattern(entity.file_path, file));
    });
    const resolvedPipelines = [...new Set(resolved.entities.map((entity) => entity.ci_cd).filter(Boolean))];
    const pipelineConflicts = resolvedPipelines.filter((pipeline) => pipeline !== declaration.deployment_pipeline);

    return {
      status: outOfScopePaths.length === 0 && undeclaredEntities.length === 0 && pipelineConflicts.length === 0 ? 'pass' : 'fail',
      changed_files: changedFiles,
      out_of_scope_paths: outOfScopePaths,
      undeclared_entities: undeclaredEntities,
      pipeline_conflicts: pipelineConflicts,
    };
  } catch (error) {
    return {
      error: 'VALIDATION_FAILED',
      message: error.message,
    };
  }
}

export async function attentionFinalizeAudit({ repo_path, testsCommand, testsResult, notes } = {}) {
  const repo = getRepoPath(repo_path);

  try {
    const validation = await attentionValidateChanges({ repo_path: repo });
    const declaration = getDeclaredScope(repo);
    const registry = declaration ? loadEntityRegistry(repo) : [];
    const declaredEntities = declaration?.affected_entities || [];
    const touchedEntities = registry.filter((entity) => declaredEntities.includes(entity.id));

    await execPython([
      'map-freshness-check',
      repo,
    ], { allowRaw: true });

    await execPython([
      'finalize-change',
      repo,
      '--tests-command',
      testsCommand || 'not_provided',
      '--tests-result',
      testsResult || 'not_run',
      '--notes',
      notes || 'none',
    ], { allowRaw: true });

    return {
      changed_files: validation.changed_files || [],
      entities_touched: touchedEntities.map((entity) => entity.id),
      pipelines_touched: [...new Set(touchedEntities.map((entity) => entity.ci_cd).filter(Boolean))],
      validation_result: validation.status || 'fail',
      test_outcomes: {
        command: testsCommand || 'not_provided',
        result: testsResult || 'not_run',
      },
      audit_artifact_path: findLatestFinalizeArtifact(repo),
      status: 'completed',
    };
  } catch (error) {
    return {
      error: 'FINALIZE_FAILED',
      message: error.message,
    };
  }
}

export async function attentionQuery({ repo_path, file }) {
  const result = await attentionResolveScope({ repo_path, files: [file] });
  if (result.error) {
    return result;
  }
  if (!result.scope.entities.length) {
    return {
      error: 'UNKNOWN_ENTITY',
      message: `File ${file} does not match any registered entity`,
    };
  }

  const registry = loadEntityRegistry(getRepoPath(repo_path));
  const entity = registry.find((item) => item.id === result.scope.entities[0]);
  return {
    entity_id: entity.id,
    file_pattern: entity.file_path,
    ci_cd: entity.ci_cd,
    endpoint: entity.endpoint,
    description: entity.description,
    entity_type: entity.type,
  };
}

export async function attentionDeclareIntent({ repo_path, entities, pipeline, summary, requiresNewEntity = false }) {
  return declareIntentInternal({
    repo: getRepoPath(repo_path),
    entities,
    pipeline,
    summary,
    requiresNewEntity,
  });
}

export async function attentionFreshness({ repo_path } = {}) {
  const repo = getRepoPath(repo_path);

  try {
    const entities = loadEntityRegistry(repo);
    const details = [];
    let passed = 0;
    let failed = 0;

    for (const entity of entities) {
      if (entity.file_path) {
        const fileExists = existsSync(join(repo, entity.file_path));
        details.push({ file: entity.file_path, exists: fileExists });
        if (fileExists) passed += 1; else failed += 1;
      }
      if (entity.ci_cd) {
        const ciCdExists = existsSync(join(repo, entity.ci_cd));
        details.push({ file: entity.ci_cd, exists: ciCdExists });
        if (ciCdExists) passed += 1; else failed += 1;
      }
    }

    try {
      await execPython(['map-freshness-check', repo], { allowRaw: true });
    } catch (freshErr) {
      // Keep filesystem validation usable even when the Python freshness gate rejects the current declaration state.
      details.push({ file: 'map-freshness-check', exists: false, warning: freshErr.message });
    }

    return {
      status: failed > 0 ? 'FAIL' : 'PASS',
      checked: details.length,
      passed,
      failed,
      details,
    };
  } catch (error) {
    return {
      error: 'FRESHNESS_FAILED',
      message: error.message,
    };
  }
}

export async function attentionAssemble({ repo_path, entities } = {}) {
  const result = await attentionAssembleContext({ repo_path, entities });
  if (result.error) {
    return result;
  }
  return { context: result.prompt_summary };
}

export async function attentionFinalize({ repo_path, testsCommand, testsResult, notes } = {}) {
  return attentionFinalizeAudit({ repo_path, testsCommand, testsResult, notes });
}

function defineTool(name, inputSchema) {
  const metadata = getToolMetadata(name);
  if (!metadata) {
    throw new Error(`Missing tool metadata for ${name}`);
  }

  return {
    name,
    description: metadata.description,
    inputSchema,
  };
}

export const toolDefinitions = [
  defineTool('attention_resolve_scope', {
    type: 'object',
    properties: {
      repo_path: { type: 'string' },
      task: { type: 'string', description: 'Optional task description.' },
      files: { type: 'array', items: { type: 'string' }, description: 'Candidate files for scope resolution.' },
    },
  }),
  defineTool('attention_get_constraints', {
    type: 'object',
    properties: {
      repo_path: { type: 'string' },
      entities: { type: 'array', items: { type: 'string' }, description: 'Optional entity IDs to inspect.' },
    },
  }),
  defineTool('attention_declare_scope', {
    type: 'object',
    properties: {
      repo_path: { type: 'string' },
      entities: { type: 'array', items: { type: 'string' } },
      pipelines: { type: 'array', items: { type: 'string' } },
      pipeline: { type: 'string' },
      summary: { type: 'string' },
      requiresNewEntity: { type: 'boolean' },
    },
    required: ['entities', 'summary'],
  }),
  defineTool('attention_assemble_context', {
    type: 'object',
    properties: {
      repo_path: { type: 'string' },
      declarationId: { type: 'string' },
      entities: { type: 'array', items: { type: 'string' } },
    },
  }),
  defineTool('attention_validate_changes', {
    type: 'object',
    properties: {
      repo_path: { type: 'string' },
      files: { type: 'array', items: { type: 'string' } },
    },
  }),
  defineTool('attention_finalize_audit', {
    type: 'object',
    properties: {
      repo_path: { type: 'string' },
      testsCommand: { type: 'string' },
      testsResult: { type: 'string', enum: ['pass', 'fail', 'not_run'] },
      notes: { type: 'string' },
    },
  }),
  defineTool('attention_query', {
    type: 'object',
    properties: {
      repo_path: { type: 'string' },
      file: { type: 'string' },
    },
    required: ['file'],
  }),
  defineTool('attention_declare_intent', {
    type: 'object',
    properties: {
      repo_path: { type: 'string' },
      entities: { type: 'array', items: { type: 'string' } },
      pipeline: { type: 'string' },
      summary: { type: 'string' },
      requiresNewEntity: { type: 'boolean' },
    },
    required: ['entities', 'pipeline', 'summary'],
  }),
  defineTool('attention_freshness', {
    type: 'object',
    properties: {
      repo_path: { type: 'string' },
    },
  }),
  defineTool('attention_assemble', {
    type: 'object',
    properties: {
      repo_path: { type: 'string' },
      entities: { type: 'array', items: { type: 'string' } },
    },
  }),
  defineTool('attention_finalize', {
    type: 'object',
    properties: {
      repo_path: { type: 'string' },
      testsCommand: { type: 'string' },
      testsResult: { type: 'string', enum: ['pass', 'fail', 'not_run'] },
      notes: { type: 'string' },
    },
  }),
];

const toolHandlers = {
  attention_resolve_scope: attentionResolveScope,
  attention_get_constraints: attentionGetConstraints,
  attention_declare_scope: attentionDeclareScope,
  attention_assemble_context: attentionAssembleContext,
  attention_validate_changes: attentionValidateChanges,
  attention_finalize_audit: attentionFinalizeAudit,
  attention_query: attentionQuery,
  attention_declare_intent: attentionDeclareIntent,
  attention_freshness: attentionFreshness,
  attention_assemble: attentionAssemble,
  attention_finalize: attentionFinalize,
};

export async function callTool(name, args = {}) {
  const handler = toolHandlers[name];
  if (!handler) {
    throw new Error(`Unknown tool: ${name}`);
  }
  return handler(args);
}

export default {
  attentionResolveScope,
  attentionGetConstraints,
  attentionDeclareScope,
  attentionAssembleContext,
  attentionValidateChanges,
  attentionFinalizeAudit,
  attentionQuery,
  attentionDeclareIntent,
  attentionFreshness,
  attentionAssemble,
  attentionFinalize,
  callTool,
  toolDefinitions,
};
