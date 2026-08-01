const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("launcher", {
  listProjects: () => ipcRenderer.invoke("projects:list"),
  createProject: (payload) => ipcRenderer.invoke("projects:create", payload),
  setDefaultProject: (name) =>
    ipcRenderer.invoke("projects:default", { name }),
  updateProject: (payload) => ipcRenderer.invoke("projects:update", payload),
  removeProject: (name) =>
    ipcRenderer.invoke("projects:remove", { name }),
  getToolStatus: () => ipcRenderer.invoke("tools:status"),
  bootstrapRuntime: () => ipcRenderer.invoke("runtime:bootstrap"),
  getRuntimeStatus: () => ipcRenderer.invoke("runtime:status"),
  updatePrivateTools: () => ipcRenderer.invoke("runtime:update"),
  getCodexUsage: () => ipcRenderer.invoke("account:usage"),
  startChat: (payload) => ipcRenderer.invoke("chat:start", payload),
  saveClipboardImage: (payload) => ipcRenderer.invoke("chat:save-image", payload),
  stopChat: (taskId) => ipcRenderer.invoke("chat:stop", { task_id: taskId }),
  onChatEvent: (callback) => {
    const listener = (_event, payload) => callback(payload);
    ipcRenderer.on("chat:event", listener);
    return () => ipcRenderer.removeListener("chat:event", listener);
  },
  getFileTree: (name) => ipcRenderer.invoke("workspace:tree", { name }),
  readFile: (name, path) => ipcRenderer.invoke("workspace:read", { name, path }),
  getRecentImages: (name, since, limit) => ipcRenderer.invoke("workspace:images", { name, since, limit }),
  getImagePreview: (name, path) => ipcRenderer.invoke("workspace:image", { name, path }),
  getGitDiff: (name, path) => ipcRenderer.invoke("workspace:diff", { name, path }),
  stageFile: (name, path) => ipcRenderer.invoke("workspace:stage", { name, path }),
  restoreFile: (name, path) => ipcRenderer.invoke("workspace:restore", { name, path }),
  runTerminal: (name, command) => ipcRenderer.invoke("workspace:terminal", { name, command }),
  getHeadroomStats: (name, port) => ipcRenderer.invoke("workspace:stats", { name, port }),
  launchProject: (name) =>
    ipcRenderer.invoke("projects:launch", { name }),
  prepareProject: (name, dryRun, initializeGit) =>
    ipcRenderer.invoke("projects:prepare", {
      name,
      dry_run: dryRun,
      initialize_git: initializeGit
    }),
  selectDirectory: () => ipcRenderer.invoke("dialog:select-directory")
});
