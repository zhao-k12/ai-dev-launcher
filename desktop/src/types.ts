export interface Project {
  name: string;
  path: string;
  created_at: string;
}

export interface ProjectList {
  projects: Project[];
  default_project: string | null;
}

export interface AddProjectInput {
  name: string;
  path: string;
  make_default: boolean;
}

export type ToolState = "available" | "missing" | "error";

export interface ToolStatus {
  key: string;
  display_name: string;
  status: ToolState;
  required: boolean;
  command: string | null;
  path: string | null;
  version: string | null;
  detail: string | null;
  install_hint: string | null;
}

export interface PreparationAction {
  kind: string;
  target: string;
  status: string;
  detail: string;
}

export interface PreparationResult {
  project: string;
  dry_run: boolean;
  actions: PreparationAction[];
}

export interface LauncherApi {
  listProjects(): Promise<ProjectList>;
  addProject(input: AddProjectInput): Promise<{ project: Project }>;
  setDefaultProject(name: string): Promise<{ project: Project }>;
  removeProject(name: string): Promise<{ project: Project }>;
  getToolStatus(): Promise<{ tools: ToolStatus[] }>;
  launchProject(name: string): Promise<{ pid: number }>;
  prepareProject(
    name: string,
    dryRun: boolean,
    initializeGit: boolean
  ): Promise<PreparationResult>;
  selectDirectory(): Promise<string | null>;
}

declare global {
  interface Window {
    launcher: LauncherApi;
  }
}
