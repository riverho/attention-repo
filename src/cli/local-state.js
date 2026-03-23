import { existsSync, mkdirSync, readFileSync, writeFileSync } from "fs";
import { homedir } from "os";
import { dirname, join, resolve } from "path";

export const ATTENTION_HOME_ENV = "ATTENTION_REPO_HOME";
export const DEFAULT_PRODUCT_KEY = "attention-repo";

export function loadVersion(rootDir) {
  const payload = JSON.parse(readFileSync(join(rootDir, "version.json"), "utf-8"));
  return String(payload.version || "").trim();
}

export function getAttentionHome() {
  return process.env[ATTENTION_HOME_ENV] || join(homedir(), ".attention");
}

export function getVaultDir() {
  return join(getAttentionHome(), "vault");
}

export function getVaultPath() {
  return join(getVaultDir(), "keys.json");
}

export function getLogsDir() {
  return join(getAttentionHome(), "logs");
}

export function getConfigPath() {
  return join(getAttentionHome(), "config.json");
}

function ensureDir(path) {
  mkdirSync(path, { recursive: true });
}

export function ensureLocalState() {
  ensureDir(getAttentionHome());
  ensureDir(getVaultDir());
  ensureDir(getLogsDir());

  if (!existsSync(getVaultPath())) {
    writeFileSync(
      getVaultPath(),
      JSON.stringify({ version: "1.0", keys: {}, active: null }, null, 2) + "\n",
      "utf-8",
    );
  }

  if (!existsSync(getConfigPath())) {
    writeFileSync(
      getConfigPath(),
      JSON.stringify({ version: "1.0", configured: false, repo_path: null }, null, 2) + "\n",
      "utf-8",
    );
  }
}

function readJson(path, fallback) {
  if (!existsSync(path)) {
    return fallback;
  }
  try {
    return JSON.parse(readFileSync(path, "utf-8"));
  } catch {
    return fallback;
  }
}

function writeJson(path, payload) {
  ensureDir(dirname(path));
  writeFileSync(path, JSON.stringify(payload, null, 2) + "\n", "utf-8");
}

export function loadVault() {
  ensureLocalState();
  return readJson(getVaultPath(), { version: "1.0", keys: {}, active: null });
}

export function loadConfig() {
  ensureLocalState();
  return readJson(getConfigPath(), { version: "1.0", configured: false, repo_path: null });
}

export function validateKeyFormat(key) {
  return /^ak_attention_repo_[A-Za-z0-9._-]+$/.test(key);
}

export function storeProductKey(product, key, overrides = {}) {
  if (!validateKeyFormat(key)) {
    throw new Error("Invalid key format. Expected ak_attention_repo_<token>.");
  }

  const vault = loadVault();
  const config = loadConfig();
  const record = {
    key,
    created: new Date().toISOString(),
    valid: overrides.valid ?? true,
    source: overrides.source || "attention-lab",
  };

  vault.keys[product] = record;
  vault.active = product;
  config.configured = true;
  writeJson(getVaultPath(), vault);
  writeJson(getConfigPath(), config);
  return record;
}

export function validateStoredKey(product) {
  const vault = loadVault();
  const record = vault.keys?.[product];
  if (!record) {
    return { status: "missing", source: "none" };
  }
  return {
    status: record.valid ? "valid" : "invalid",
    source: record.source || "unknown",
    record,
  };
}

export function findRepoRoot(startDir) {
  let current = resolve(startDir);

  while (true) {
    if (existsSync(join(current, "!MAP.md"))) {
      return current;
    }

    const parent = dirname(current);
    if (parent === current) {
      return null;
    }
    current = parent;
  }
}

export function detectRepoPath(startDir) {
  return findRepoRoot(startDir);
}

export function getMcpEntrypoint(rootDir) {
  const candidates = [
    join(rootDir, "mcp-server", "index.js"),
  ];
  return candidates.find((path) => existsSync(path)) || null;
}
