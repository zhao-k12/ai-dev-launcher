import { vi } from "vitest";

Object.defineProperty(window, "launcher", {
  writable: true,
  value: {
    listProjects: vi.fn(),
    addProject: vi.fn(),
    setDefaultProject: vi.fn(),
    removeProject: vi.fn(),
    getToolStatus: vi.fn(),
    launchProject: vi.fn(),
    prepareProject: vi.fn(),
    selectDirectory: vi.fn()
  }
});
