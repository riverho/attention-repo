import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";

const execFileAsync = promisify(execFile);
const pluginRoot = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(pluginRoot, "..", "..");
const bridgeScript = path.join(repoRoot, "scripts", "openclaw_router_bridge.py");

type TelegramButtons = Array<Array<{ text: string; callback_data: string }>>;

type BridgeReply = {
  text: string;
  channelData?: {
    telegram?: {
      buttons?: TelegramButtons;
    };
  };
};

async function runBridge(ctx: {
  commandBody: string;
  senderId?: string;
  channel: string;
  messageThreadId?: number;
}): Promise<BridgeReply> {
  const args = [
    bridgeScript,
    "--text",
    ctx.commandBody.trim() || "/attention_repo",
    "--user-id",
    ctx.senderId?.trim() || "unknown",
    "--platform",
    ctx.channel,
  ];

  if (ctx.messageThreadId != null) {
    args.push("--message-id", String(ctx.messageThreadId));
  }

  const { stdout } = await execFileAsync("python3", args, {
    cwd: repoRoot,
    timeout: 30_000,
    maxBuffer: 1024 * 1024,
  });

  const parsed = JSON.parse(stdout) as BridgeReply;
  if (!parsed || typeof parsed.text !== "string") {
    throw new Error("Bridge returned invalid payload.");
  }
  return parsed;
}

export default function register(api: OpenClawPluginApi) {
  api.registerCommand({
    name: "attention_repo",
    description: "Show the attention-repo project menu.",
    acceptsArgs: true,
    handler: async (ctx) =>
      runBridge({
        commandBody: ctx.commandBody,
        senderId: ctx.senderId ?? undefined,
        channel: ctx.channel,
        messageThreadId: ctx.messageThreadId,
      }),
  });
}
