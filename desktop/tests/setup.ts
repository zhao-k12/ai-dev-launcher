import { vi } from "vitest";

Object.defineProperty(window, "launcher", {
  writable: true,
  value: {
    listProjects: vi.fn(),
    createProject: vi.fn(),
    setDefaultProject: vi.fn(),
    removeProject: vi.fn(),
    getToolStatus: vi.fn(),
    bootstrapRuntime: vi.fn(),
    getRuntimeStatus: vi.fn(),
    updatePrivateTools: vi.fn(),
    getCodexUsage: vi.fn(),
    startChat: vi.fn(),
    stopChat: vi.fn(),
    onChatEvent: vi.fn(() => () => undefined),
    getFileTree: vi.fn(),
    readFile: vi.fn(),
    getGitDiff: vi.fn(),
    stageFile: vi.fn(),
    restoreFile: vi.fn(),
    runTerminal: vi.fn(),
    getHeadroomStats: vi.fn(),
    launchProject: vi.fn(),
    prepareProject: vi.fn(),
    selectDirectory: vi.fn()
  }
});
