import { execFile, spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { randomUUID } from "node:crypto";
import { delimiter } from "node:path";
import type { BrowserWindow } from "electron";
import { callPython } from "./pythonBridge.js";

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
}

export class ChatSessionManager {
  private active = new Map<string, ChildProcessWithoutNullStreams>();

  constructor(private readonly window: BrowserWindow) {}

  async start(input: StartInput): Promise<{ task_id: string }> {
    const plan = await callPython<LaunchPlan>("chat.plan", { ...input });
    const taskId = input.task_id ?? randomUUID();
    const environment = { ...process.env } as Record<string, string>;
    environment.PATH = [...plan.path_prepend, environment.PATH ?? ""].filter(Boolean).join(delimiter);
    for (const [key, value] of Object.entries(plan.environment_overrides)) environment[key] = value;
    const child = spawn(plan.command[0], plan.command.slice(1), { cwd: plan.cwd, env: environment, windowsHide: true });
    child.stdin.end();
    this.active.set(taskId, child);
    let stdout = "";
    let stderr = "";
    const send = (event: Record<string, unknown>) => this.window.webContents.send("chat:event", { task_id: taskId, ...event });

    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString("utf8");
      const lines = stdout.split(/\r?\n/);
      stdout = lines.pop() ?? "";
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try { send({ type: "codex", event: JSON.parse(trimmed) }); }
        catch { send({ type: "log", stream: "stdout", text: trimmed }); }
      }
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString("utf8");
      const lines = stderr.split(/\r?\n/);
      stderr = lines.pop() ?? "";
      for (const line of lines) if (line.trim()) send({ type: "log", stream: "stderr", text: line.trim() });
    });
    child.on("error", (error) => send({ type: "error", message: error.message }));
    child.on("close", (code) => {
      if (stdout.trim()) send({ type: "log", stream: "stdout", text: stdout.trim() });
      if (stderr.trim()) send({ type: "log", stream: "stderr", text: stderr.trim() });
      this.active.delete(taskId);
      send({ type: "complete", exit_code: code ?? -1 });
    });
    return { task_id: taskId };
  }

  stop(taskId: string): { stopped: boolean } {
    const child = this.active.get(taskId);
    if (!child) return { stopped: false };
    this.stopProcess(child);
    return { stopped: true };
  }

  stopAll(): void {
    for (const child of this.active.values()) this.stopProcess(child);
    this.active.clear();
  }

  private stopProcess(child: ChildProcessWithoutNullStreams): void {
    if (process.platform === "win32" && child.pid) {
      execFile("taskkill", ["/pid", String(child.pid), "/t", "/f"], { windowsHide: true }, () => undefined);
    } else child.kill();
  }
}
