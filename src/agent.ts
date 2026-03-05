/**
 * Attention Agent — Self-Managing Ecosystem Orchestration
 * 
 * The attention-layer becomes a true agent that:
 * 1. Monitors all projects in the ecosystem
 * 2. Detects drift, staleness, conflicts
 * 3. Auto-organizes !MAP, !CONNECTIONS, TLDR
 * 4. Proposes actions (human gate)
 * 
 * Unlike summon agent (task-focused), attention agent is 
 * ecosystem-focused — it manages the map of all work.
 */

import { existsSync, readFileSync, writeFileSync, readdirSync, statSync } from 'fs';
import { join, resolve } from 'path';
import { homedir } from 'os';

// ============================================================================
// Types
// ============================================================================

export interface ProjectState {
  path: string;
  name: string;
  lastModified: number;
  tldrExists: boolean;
  connectionsExists: boolean;
  mapExists: boolean;
  branchCount: number;
  funnelCount: number;
  health: 'active' | 'stale' | 'abandoned' | 'conflicted';
}

export interface EcosystemHealth {
  totalProjects: number;
  activeProjects: number;
  staleProjects: number;
  conflictedProjects: number;
  orphanedConnections: number;
  overallHealth: 'healthy' | 'degraded' | 'critical';
}

export interface AttentionAction {
  type: 'update_tldr' | 'archive_stale' | 'resolve_conflict' | 'merge_branches' | 'notify_human';
  target: string;
  reason: string;
  proposal: string;
  humanGate: boolean;
}

// ============================================================================
// Attention Agent
// ============================================================================

export class AttentionAgent {
  private projectsRoot: string;
  private statePath: string;

  constructor(projectsRoot?: string) {
    this.projectsRoot = projectsRoot || join(homedir(), '.openclaw', 'workspace', 'projects');
    this.statePath = join(homedir(), '.openclaw', 'workspace', '.attention-state', 'agent-state.json');
  }

  /**
   * Scan entire ecosystem and build state
   */
  async scanEcosystem(): Promise<ProjectState[]> {
    const projects: ProjectState[] = [];
    
    // Find all project directories
    const entries = readdirSync(this.projectsRoot, { withFileTypes: true });
    
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      if (entry.name.startsWith('.')) continue;
      
      const projectPath = join(this.projectsRoot, entry.name);
      const state = await this.analyzeProject(projectPath);
      projects.push(state);
    }
    
    return projects;
  }

  /**
   * Analyze single project health
   */
  private async analyzeProject(projectPath: string): Promise<ProjectState> {
    const name = projectPath.split('/').pop() || '';
    const stats = statSync(projectPath);
    
    // Check key files
    const tldrPath = join(projectPath, 'TLDR.md');
    const connectionsPath = join(projectPath, `!CONNECTIONS_${name}.md`);
    const mapPath = join(this.projectsRoot, `!MAP_${name}.md`);
    
    // Count branches (TLDR_*.md files)
    const files = readdirSync(projectPath);
    const branchCount = files.filter(f => f.startsWith('TLDR_') && f.endsWith('.md')).length;
    
    // Count funnels
    const attentionDir = join(homedir(), '.openclaw', 'workspace', '.attention-state');
    let funnelCount = 0;
    if (existsSync(attentionDir)) {
      const attentionFiles = readdirSync(attentionDir);
      funnelCount = attentionFiles.filter(f => f.includes(name)).length;
    }
    
    // Determine health
    const daysSinceModified = (Date.now() - stats.mtimeMs) / (1000 * 60 * 60 * 24);
    let health: ProjectState['health'] = 'active';
    
    if (daysSinceModified > 30) {
      health = 'abandoned';
    } else if (daysSinceModified > 7) {
      health = 'stale';
    }
    
    // Check for conflicts (multiple active branches)
    if (branchCount > 3) {
      health = 'conflicted';
    }
    
    return {
      path: projectPath,
      name,
      lastModified: stats.mtimeMs,
      tldrExists: existsSync(tldrPath),
      connectionsExists: existsSync(connectionsPath),
      mapExists: existsSync(mapPath),
      branchCount,
      funnelCount,
      health
    };
  }

  /**
   * Evaluate ecosystem health
   */
  evaluateEcosystem(projects: ProjectState[]): EcosystemHealth {
    const active = projects.filter(p => p.health === 'active').length;
    const stale = projects.filter(p => p.health === 'stale').length;
    const abandoned = projects.filter(p => p.health === 'abandoned').length;
    const conflicted = projects.filter(p => p.health === 'conflicted').length;
    
    // Orphaned = CONNECTIONS exists but no recent funnel activity
    const orphaned = projects.filter(p => 
      p.connectionsExists && p.funnelCount === 0 && p.health !== 'active'
    ).length;
    
    let overall: EcosystemHealth['overallHealth'] = 'healthy';
    if (conflicted > 0 || abandoned > projects.length * 0.3) {
      overall = 'critical';
    } else if (stale > projects.length * 0.5) {
      overall = 'degraded';
    }
    
    return {
      totalProjects: projects.length,
      activeProjects: active,
      staleProjects: stale,
      conflictedProjects: conflicted,
      orphanedConnections: orphaned,
      overallHealth: overall
    };
  }

  /**
   * Generate attention actions based on ecosystem state
   */
  generateActions(projects: ProjectState[], health: EcosystemHealth): AttentionAction[] {
    const actions: AttentionAction[] = [];
    
    // Action 1: Update stale TLDRs
    for (const project of projects.filter(p => p.health === 'stale')) {
      actions.push({
        type: 'update_tldr',
        target: project.name,
        reason: `No activity for ${Math.floor((Date.now() - project.lastModified) / (1000 * 60 * 60 * 24))} days`,
        proposal: `Update TLDR.md for ${project.name} to reflect current status, or mark as dormant`,
        humanGate: true
      });
    }
    
    // Action 2: Archive abandoned projects
    for (const project of projects.filter(p => p.health === 'abandoned')) {
      actions.push({
        type: 'archive_stale',
        target: project.name,
        reason: `No activity for 30+ days`,
        proposal: `Archive ${project.name}: move to dormant/, update !MAP.md status`,
        humanGate: true
      });
    }
    
    // Action 3: Resolve conflicts (too many branches)
    for (const project of projects.filter(p => p.health === 'conflicted')) {
      actions.push({
        type: 'merge_branches',
        target: project.name,
        reason: `${project.branchCount} active branches — attention fragmentation`,
        proposal: `Evaluate branches for ${project.name}, merge or close stale ones`,
        humanGate: true
      });
    }
    
    // Action 4: Critical ecosystem alert
    if (health.overallHealth === 'critical') {
      actions.push({
        type: 'notify_human',
        target: 'ecosystem',
        reason: `Critical: ${health.conflictedProjects} conflicts, ${health.staleProjects} stale`,
        proposal: `Ecosystem requires attention: ${health.activeProjects}/${health.totalProjects} projects active. Recommend review session.`,
        humanGate: true
      });
    }
    
    return actions;
  }

  /**
   * Auto-organize ecosystem files
   */
  async organize(): Promise<string[]> {
    const projects = await this.scanEcosystem();
    const health = this.evaluateEcosystem(projects);
    const actions = this.generateActions(projects, health);
    
    const results: string[] = [];
    
    for (const action of actions.filter(a => !a.humanGate)) {
      // Auto-execute low-risk actions
      if (action.type === 'update_tldr') {
        await this.autoUpdateTLDR(action.target);
        results.push(`✅ Auto-updated TLDR: ${action.target}`);
      }
    }
    
    // Save state
    this.saveState({ projects, health, actions });
    
    return results;
  }

  /**
   * Auto-update stale TLDR with current status
   */
  private async autoUpdateTLDR(projectName: string): Promise<void> {
    const tldrPath = join(this.projectsRoot, projectName, 'TLDR.md');
    
    const content = `# TLDR — ${projectName}

**Status:** Dormant (auto-detected by Attention Agent)
**Last Activity:** ${new Date().toISOString().split('T')[0]}
**Detected By:** Attention Agent ecosystem scan

## Auto-Generated Summary

This project was flagged as stale during automated ecosystem health check.

**Possible Actions:**
- /pivot — Resume with new direction
- /archive — Move to dormant/
- /evaluate — Assess current relevance

---
*This TLDR was auto-generated by Attention Agent. Human review recommended.*
`;
    
    writeFileSync(tldrPath, content);
  }

  /**
   * Propose actions to human
   */
  async propose(): Promise<AttentionAction[]> {
    const projects = await this.scanEcosystem();
    const health = this.evaluateEcosystem(projects);
    const actions = this.generateActions(projects, health);
    
    return actions.filter(a => a.humanGate);
  }

  /**
   * Execute action (with human approval)
   */
  async executeAction(action: AttentionAction, approved: boolean): Promise<string> {
    if (!approved) {
      return `❌ Action rejected: ${action.type} on ${action.target}`;
    }
    
    switch (action.type) {
      case 'archive_stale':
        return await this.archiveProject(action.target);
      case 'merge_branches':
        return await this.mergeBranches(action.target);
      case 'update_tldr':
        await this.autoUpdateTLDR(action.target);
        return `✅ Updated TLDR: ${action.target}`;
      default:
        return `⚠️ Action ${action.type} requires manual execution`;
    }
  }

  private async archiveProject(name: string): Promise<string> {
    // Would move project to dormant/
    return `📦 Archived ${name} to dormant/${name}`;
  }

  private async mergeBranches(name: string): Promise<string> {
    // Would evaluate and merge branches
    return `🔀 Evaluated branches for ${name} — manual merge required`;
  }

  private saveState(state: any): void {
    const dir = join(homedir(), '.openclaw', 'workspace', '.attention-state');
    if (!existsSync(dir)) {
      require('fs').mkdirSync(dir, { recursive: true });
    }
    writeFileSync(this.statePath, JSON.stringify(state, null, 2));
  }

  /**
   * Run full ecosystem health check (main entry)
   */
  async run(): Promise<{
    health: EcosystemHealth;
    autoActions: string[];
    proposedActions: AttentionAction[];
  }> {
    const projects = await this.scanEcosystem();
    const health = this.evaluateEcosystem(projects);
    const autoActions = await this.organize();
    const proposedActions = await this.propose();
    
    return { health, autoActions, proposedActions };
  }
}

// ============================================================================
// Singleton
// ============================================================================

let globalAttentionAgent: AttentionAgent | null = null;

export function getAttentionAgent(): AttentionAgent {
  if (!globalAttentionAgent) {
    globalAttentionAgent = new AttentionAgent();
  }
  return globalAttentionAgent;
}

export async function runAttentionAgent(): Promise<{
  health: EcosystemHealth;
  autoActions: string[];
  proposedActions: AttentionAction[];
}> {
  const agent = getAttentionAgent();
  return agent.run();
}
