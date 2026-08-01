import { spawn } from "node:child_process";

export interface CodexUsage {
  available: boolean;
  used_percent: number | null;
  remaining_percent: number | null;
  resets_at: number | null;
  window_minutes: number | null;
  plan_type: string | null;
}

export function readCodexUsage(): Promise<CodexUsage> {
  return new Promise((resolve) => {
    const environment = { ...process.env };
    for (const key of Object.keys(environment)) if (key.startsWith("_PYI_")) delete environment[key];
    const executable = process.platform === "win32" ? (process.env.ComSpec || "cmd.exe") : "codex";
    const args = process.platform === "win32"
      ? ["/d", "/s", "/c", "codex.cmd app-server --listen stdio://"]
      : ["app-server", "--listen", "stdio://"];
    const child = spawn(executable, args, { env: environment, windowsHide: true, stdio: ["pipe", "pipe", "ignore"] });
    let buffer = "";
    let initialized = false;
    let settled = false;
    const finish = (value: CodexUsage) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      child.kill();
      resolve(value);
    };
    const unavailable = (): CodexUsage => ({ available: false, used_percent: null, remaining_percent: null, resets_at: null, window_minutes: null, plan_type: null });
    const timeout = setTimeout(() => finish(unavailable()), 8000);
    child.on("error", () => finish(unavailable()));
    child.stdout.setEncoding("utf8");
    child.stdout.on("data", (chunk: string) => {
      buffer += chunk;
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.trim()) continue;
        let message: Record<string, unknown>;
        try { message = JSON.parse(line) as Record<string, unknown>; } catch { continue; }
        if (message.id === 1 && !initialized) {
          initialized = true;
          child.stdin.write(`${JSON.stringify({ method: "initialized", params: {} })}\n`);
          child.stdin.write(`${JSON.stringify({ id: 2, method: "account/rateLimits/read", params: null })}\n`);
        }
        if (message.id === 2) {
          const result = (message.result ?? {}) as Record<string, unknown>;
          const limits = (result.rateLimits ?? {}) as Record<string, unknown>;
          const primary = (limits.primary ?? {}) as Record<string, unknown>;
          const used = typeof primary.usedPercent === "number" ? primary.usedPercent : null;
          finish({
            available: used !== null,
            used_percent: used,
            remaining_percent: used === null ? null : Math.max(0, 100 - used),
            resets_at: typeof primary.resetsAt === "number" ? primary.resetsAt : null,
            window_minutes: typeof primary.windowDurationMins === "number" ? primary.windowDurationMins : null,
            plan_type: typeof limits.planType === "string" ? limits.planType : null
          });
        }
      }
    });
    child.stdin.write(`${JSON.stringify({ id: 1, method: "initialize", params: { clientInfo: { name: "ai-dev-launcher", title: "AI Dev Launcher", version: "2.0" } } })}\n`);
  });
}
