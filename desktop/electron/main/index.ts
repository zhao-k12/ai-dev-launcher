import { app, BrowserWindow, dialog, ipcMain } from "electron";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { callPython } from "./pythonBridge.js";

const currentDir = dirname(fileURLToPath(import.meta.url));

function createWindow(): void {
  const window = new BrowserWindow({
    width: 1180,
    height: 760,
    minWidth: 920,
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

  const developmentUrl = process.env.VITE_DEV_SERVER_URL;
  if (developmentUrl) {
    void window.loadURL(developmentUrl);
  } else {
    void window.loadFile(join(currentDir, "../../dist/index.html"));
  }
}

app.whenReady().then(() => {
  ipcMain.handle("projects:list", () => callPython("projects.list"));
  ipcMain.handle("projects:add", (_event, payload) =>
    callPython("projects.add", payload)
  );
  ipcMain.handle("projects:default", (_event, payload) =>
    callPython("projects.default", payload)
  );
  ipcMain.handle("projects:remove", (_event, payload) =>
    callPython("projects.remove", payload)
  );
  ipcMain.handle("tools:status", () => callPython("tools.status"));
  ipcMain.handle("projects:launch", (_event, payload) =>
    callPython("projects.launch", payload)
  );
  ipcMain.handle("projects:prepare", (_event, payload) =>
    callPython("projects.prepare", payload)
  );
  ipcMain.handle("dialog:select-directory", async () => {
    const result = await dialog.showOpenDialog({
      title: "选择项目目录",
      properties: ["openDirectory", "createDirectory"]
    });
    return result.canceled ? null : result.filePaths[0];
  });
  createWindow();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
