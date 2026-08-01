import { app, BrowserWindow, dialog, ipcMain } from "electron";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { callPython } from "./pythonBridge.js";
import { ChatSessionManager } from "./chatSessions.js";

const currentDir = dirname(fileURLToPath(import.meta.url));

function createWindow(): void {
  const window = new BrowserWindow({
    width: 1440,
    height: 860,
    minWidth: 1100,
    minHeight: 620,
    backgroundColor: "#f3f6fb",
    title: "AI Dev Launcher",
    webPreferences: {
      preload: join(currentDir, "../../electron/preload/index.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });
  const chats = new ChatSessionManager(window);
  ipcMain.handle("chat:start", (_event, payload) => chats.start(payload));
  ipcMain.handle("chat:stop", (_event, payload) => chats.stop(payload.task_id));
  window.on("closed", () => chats.stopAll());

  const developmentUrl = process.env.VITE_DEV_SERVER_URL;
  if (developmentUrl) {
    void window.loadURL(developmentUrl);
  } else {
    void window.loadFile(join(currentDir, "../../dist/index.html"));
  }
}

app.whenReady().then(() => {
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
  ipcMain.handle("workspace:tree", (_event, payload) => callPython("workspace.tree", payload));
  ipcMain.handle("workspace:read", (_event, payload) => callPython("workspace.read", payload));
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
