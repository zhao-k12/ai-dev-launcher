import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { app } from "electron";

type BridgeResponse<T> =
  | { ok: true; data: T }
  | { ok: false; error: string };

const currentDir = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(currentDir, "../../..");

function bridgeCommand(): {
  executable: string;
  args: string[];
  cwd: string;
} {
  if (app.isPackaged) {
    return {
      executable: join(process.resourcesPath, "ai-dev-core.exe"),
      args: [],
      cwd: app.getPath("userData")
    };
  }
  if (process.env.AI_DEV_PYTHON) {
    return {
      executable: process.env.AI_DEV_PYTHON,
      args: ["-m", "ai_dev_launcher.bridge"],
      cwd: repositoryRoot
    };
  }
  const localPython = resolve(repositoryRoot, ".venv/Scripts/python.exe");
  return {
    executable: existsSync(localPython) ? localPython : "python",
    args: ["-m", "ai_dev_launcher.bridge"],
    cwd: repositoryRoot
  };
}

export function callPython<T>(
  action: string,
  payload: Record<string, unknown> = {}
): Promise<T> {
  return new Promise((resolvePromise, reject) => {
    const command = bridgeCommand();
    const bridgeEnvironment = { ...process.env };
    for (const key of Object.keys(bridgeEnvironment)) {
      if (key.startsWith("_PYI_")) delete bridgeEnvironment[key];
    }
    bridgeEnvironment.PYINSTALLER_RESET_ENVIRONMENT = "1";
    const child = execFile(
      command.executable,
      command.args,
      {
        cwd: command.cwd,
        env: bridgeEnvironment,
        encoding: "utf8",
        timeout: 15000,
        windowsHide: true
      },
      (error, stdout, stderr) => {
        let response: BridgeResponse<T>;
        try {
          response = JSON.parse(stdout) as BridgeResponse<T>;
        } catch {
          reject(
            new Error(
              stderr.trim() ||
                error?.message ||
                "Python core returned an invalid response."
            )
          );
          return;
        }
        if (!response.ok) {
          reject(new Error(response.error));
          return;
        }
        resolvePromise(response.data);
      }
    );
    child.stdin?.end(JSON.stringify({ action, payload }));
  });
}
