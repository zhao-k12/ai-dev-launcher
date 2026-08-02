import { execFile, spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { randomUUID } from "node:crypto";
import { delimiter } from "node:path";
import { StringDecoder } from "node:string_decoder";
import type { BrowserWindow } from "electron";
import { callPython } from "./pythonBridge.js";
import { isExpectedHeadroomWebSocketFallback } from "./chatFilters.js";

interface LaunchPlan {
  cwd: string;
  command: string[];
  path_prepend: string[];
  environment_overrides: Record<string, string>;
}

interface StartInput {
  task_id?: string;
  name: string;
  prompt: string;
  permission: "standard" | "full";
  session_id?: string;
  images?: string[];
}

function isRoutineWrapperOutput(line: string): boolean {
  return [
    /HEADROOM WRAP: CODEX/i,
    /^[╔╗╚╝║═\s]+$/u,
    /^Proxy (?:already running|ready)/i,
    /^Dashboard:/i,
    /^Launching CODEX/i,
    /^OPENAI_BASE_URL=/i,
    /^Extra args:/i
  ].some((pattern) => pattern.test(line));
}

export class ChatSessionManager {
  private active = new Map<string, ChildProcessWithoutNullStreams>();
  private activeProjects = new Map<string, string>();
  private cancelled = new Set<string>();

  constructor(private readonly window: BrowserWindow) {}

  async start(input: StartInput): Promise<{ task_id: string }> {
    const plan = await callPython<LaunchPlan>("chat.plan", { ...input });
    const taskId = input.task_id ?? randomUUID();
    const environment = { ...process.env } as Record<string, string>;
    environment.PATH = [...plan.path_prepend, environment.PATH ?? ""].filter(Boolean).join(delimiter);
    for (const [key, value] of Object.entries(plan.environment_overrides)) environment[key] = value;
    const child = spawn(plan.command[0], plan.command.slice(1), { cwd: plan.cwd, env: environment, windowsHide: true });
    // Headroom's Windows wrapper can lose long or non-ASCII positional prompts.
    // The launch plan therefore uses Codex's `-` prompt and streams the exact
    // text over stdin for both fresh and resumed sessions.
    child.stdin.end(input.prompt, "utf8");
    this.active.set(taskId, child);
    this.activeProjects.set(taskId, input.name);
    let stdout = "";
    let stderr = "";
    const stdoutDecoder = new StringDecoder("utf8");
    const stderrDecoder = new StringDecoder("utf8");
    const stderrLines: string[] = [];
    const send = (event: Record<string, unknown>) => this.window.webContents.send("chat:event", { task_id: taskId, ...event });

    child.stdout.on("data", (chunk: Buffer) => {
      stdout += stdoutDecoder.write(chunk);
      const lines = stdout.split(/\r?\n/);
      stdout = lines.pop() ?? "";
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
          const event = JSON.parse(trimmed) as Record<string, unknown>;
          if (!isExpectedHeadroomWebSocketFallback(event)) {
            send({ type: "codex", event });
          }
        }
        catch {
          if (!isRoutineWrapperOutput(trimmed)) {
            send({ type: "log", stream: "stdout", text: trimmed });
          }
        }
      }
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += stderrDecoder.write(chunk);
      const lines = stderr.split(/\r?\n/);
      stderr = lines.pop() ?? "";
      for (const line of lines) if (line.trim()) stderrLines.push(line.trim());
    });
    child.on("error", (error) => {
      if (!this.cancelled.has(taskId)) send({ type: "error", message: error.message });
    });
    child.on("close", (code) => {
      stdout += stdoutDecoder.end();
      stderr += stderrDecoder.end();
      if (stdout.trim()) send({ type: "log", stream: "stdout", text: stdout.trim() });
      if (stderr.trim()) stderrLines.push(stderr.trim());
      this.active.delete(taskId);
      this.activeProjects.delete(taskId);
      const cancelled = this.cancelled.delete(taskId);
      const meaningfulError = stderrLines
        .filter((line) => !/\b(?:WARN|INFO)\b/.test(line))
        .slice(-4)
        .join("\n");
      send({ type: "complete", exit_code: code ?? -1, message: meaningfulError || undefined, cancelled });
    });
    return { task_id: taskId };
  }

  stop(taskId: string): { stopped: boolean } {
    const child = this.active.get(taskId);
    if (!child) return { stopped: false };
    this.cancelled.add(taskId);
    this.stopProcess(child);
    return { stopped: true };
  }

  stopAll(): void {
    for (const child of this.active.values()) this.stopProcess(child);
    this.active.clear();
    this.activeProjects.clear();
    this.cancelled.clear();
  }

  hasActiveProject(name: string): boolean {
    return [...this.activeProjects.values()].some((project) => project.toLocaleLowerCase() === name.toLocaleLowerCase());
  }

  private stopProcess(child: ChildProcessWithoutNullStreams): void {
    if (process.platform === "win32" && child.pid) {
      execFile("taskkill", ["/pid", String(child.pid), "/t", "/f"], { windowsHide: true }, () => undefined);
    } else child.kill();
  }
}
