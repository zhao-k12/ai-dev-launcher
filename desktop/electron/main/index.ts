import { app, BrowserWindow, clipboard, dialog, ipcMain, Menu, nativeImage, shell } from "electron";
import { randomUUID } from "node:crypto";
import { mkdir, readdir, stat, unlink, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { callPython } from "./pythonBridge.js";
import { ChatSessionManager } from "./chatSessions.js";
import { readCodexUsage } from "./codexUsage.js";

const currentDir = dirname(fileURLToPath(import.meta.url));
let mainWindow: BrowserWindow | null = null;

function clipboardImageDirectory(): string {
  return join(app.getPath("temp"), "ai-dev-launcher", "clipboard-images");
}

async function cleanupClipboardImages(): Promise<void> {
  const directory = clipboardImageDirectory();
  const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000;
  try {
    const names = await readdir(directory);
    await Promise.all(names.map(async (name) => {
      const path = join(directory, name);
      try {
        if ((await stat(path)).mtimeMs < cutoff) await unlink(path);
      } catch { /* A concurrently used or removed temporary image is harmless. */ }
    }));
  } catch { /* The directory does not exist on a fresh installation. */ }
}

function createWindow(): void {
  const window = new BrowserWindow({
    width: 1440,
    height: 860,
    minWidth: 1100,
    minHeight: 620,
    backgroundColor: "#f3f6fb",
    title: `AI Dev Launcher v${app.getVersion()}`,
    webPreferences: {
      preload: join(currentDir, "../../electron/preload/index.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });
  mainWindow = window;
  const chats = new ChatSessionManager(window);
  ipcMain.handle("projects:update", (_event, payload) => {
    if (chats.hasActiveProject(String(payload?.current_name ?? ""))) {
      throw new Error("请先停止该项目正在运行的 Codex 任务，再编辑或移动项目");
    }
    return callPython("projects.update", payload);
  });
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//i.test(url)) void shell.openExternal(url);
    return { action: "deny" };
  });
  window.webContents.on("will-navigate", (event, url) => {
    if (url !== window.webContents.getURL()) event.preventDefault();
  });
  ipcMain.handle("chat:start", (_event, payload) => chats.start(payload));
  ipcMain.handle("chat:stop", (_event, payload) => chats.stop(payload.task_id));
  window.on("closed", () => {
    mainWindow = null;
    chats.stopAll();
    ipcMain.removeHandler("projects:update");
  });

  const developmentUrl = process.env.VITE_DEV_SERVER_URL;
  if (developmentUrl) {
    void window.loadURL(developmentUrl);
  } else {
    void window.loadFile(join(currentDir, "../../dist/index.html"));
  }
}

const singleInstance = app.requestSingleInstanceLock();
if (!singleInstance) app.quit();
else app.on("second-instance", () => {
  if (!mainWindow) return;
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
});

if (singleInstance) app.whenReady().then(() => {
  void cleanupClipboardImages();
  Menu.setApplicationMenu(null);
  ipcMain.handle("projects:list", () => callPython("projects.list"));
  ipcMain.handle("projects:create", (_event, payload) =>
    callPython("projects.create", payload)
  );
  ipcMain.handle("projects:default", (_event, payload) =>
    callPython("projects.default", payload)
  );
  ipcMain.handle("projects:remove", (_event, payload) =>
    callPython("projects.remove", payload)
  );
  ipcMain.handle("tools:status", () => callPython("tools.status"));
  ipcMain.handle("runtime:bootstrap", () => callPython("runtime.bootstrap"));
  ipcMain.handle("runtime:status", () => callPython("runtime.status"));
  ipcMain.handle("runtime:update", () => callPython("runtime.update"));
  ipcMain.handle("account:usage", () => readCodexUsage());
  ipcMain.handle("clipboard:write", (_event, payload) => {
    clipboard.writeText(String(payload?.text ?? ""));
    return { copied: true };
  });
  ipcMain.handle("chat:save-image", async (_event, payload) => {
    const match = /^data:(image\/(?:png|jpeg|webp|gif));base64,([A-Za-z0-9+/=]+)$/.exec(String(payload?.data_url ?? ""));
    if (!match) throw new Error("Unsupported clipboard image format");
    const extensions: Record<string, string> = { "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif" };
    const contents = Buffer.from(match[2], "base64");
    if (contents.byteLength > 10 * 1024 * 1024) throw new Error("Clipboard image exceeds the 10 MB limit");
    const directory = clipboardImageDirectory();
    await mkdir(directory, { recursive: true });
    const path = join(directory, `${randomUUID()}.${extensions[match[1]]}`);
    await writeFile(path, contents);
    return { path };
  });
  ipcMain.handle("workspace:tree", (_event, payload) => callPython("workspace.tree", payload));
  ipcMain.handle("workspace:read", (_event, payload) => callPython("workspace.read", payload));
  ipcMain.handle("workspace:images", (_event, payload) => callPython("workspace.images", payload));
  ipcMain.handle("workspace:image", async (_event, payload) => {
    const result = await callPython<{ path: string }>("workspace.image-path", payload);
    const source = nativeImage.createFromPath(result.path);
    if (source.isEmpty()) throw new Error("图片无法读取或格式不受支持");
    const size = source.getSize();
    const preview = size.width > 1600 ? source.resize({ width: 1600, quality: "good" }) : source;
    return { data_url: `data:image/jpeg;base64,${preview.toJPEG(84).toString("base64")}`, width: size.width, height: size.height };
  });
  ipcMain.handle("workspace:diff", (_event, payload) => callPython("workspace.diff", payload));
  ipcMain.handle("workspace:stage", (_event, payload) => callPython("workspace.stage", payload));
  ipcMain.handle("workspace:restore", (_event, payload) => callPython("workspace.restore", payload));
  ipcMain.handle("workspace:terminal", (_event, payload) => callPython("workspace.terminal", payload));
  ipcMain.handle("workspace:stats", (_event, payload) => callPython("workspace.stats", payload));
  ipcMain.handle("projects:launch", (_event, payload) =>
    callPython("projects.launch", payload)
  );
  ipcMain.handle("projects:prepare", (_event, payload) =>
    callPython("projects.prepare", payload)
  );
  ipcMain.handle("dialog:select-directory", async () => {
    const result = await dialog.showOpenDialog({
      title: "选择保存位置",
      properties: ["openDirectory", "createDirectory"]
    });
    return result.canceled ? null : result.filePaths[0];
  });
  createWindow();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
