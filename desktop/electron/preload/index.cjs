const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("launcher", {
  listProjects: () => ipcRenderer.invoke("projects:list"),
  addProject: (payload) => ipcRenderer.invoke("projects:add", payload),
  setDefaultProject: (name) =>
    ipcRenderer.invoke("projects:default", { name }),
  removeProject: (name) =>
    ipcRenderer.invoke("projects:remove", { name }),
  getToolStatus: () => ipcRenderer.invoke("tools:status"),
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
