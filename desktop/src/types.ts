export interface Project {
  name: string;
  path: string;
  created_at: string;
}

export interface ProjectList {
  projects: Project[];
  default_project: string | null;
}

export interface CreateProjectInput {
  name: string;
  parent: string;
}
export interface UpdateProjectInput { current_name: string; name: string; parent: string; }

export interface RuntimeCheck {
  key: string;
  label: string;
  status: "ready" | "warning" | "error";
  detail: string | null;
}

export interface RuntimeStatus {
  status: "ready" | "attention";
  checks: RuntimeCheck[];
  headroom_version: string | null;
  headroom_compression?: boolean;
  codex_version: string | null;
  headroom_port: number | null;
  isolation: "process";
  automatic_updates: boolean;
  last_checked: string;
  recovered?: boolean;
}

export interface CodexUsage {
  available: boolean;
  used_percent: number | null;
  remaining_percent: number | null;
  resets_at: number | null;
  window_minutes: number | null;
  plan_type: string | null;
}

export interface ChatEvent {
  task_id: string;
  type: "codex" | "log" | "error" | "complete";
  event?: Record<string, unknown>;
  text?: string;
  message?: string;
  exit_code?: number;
  cancelled?: boolean;
}
export interface FileTreeItem { path: string; name: string; kind: "file" | "directory"; }
export interface ImageArtifact { path: string; name: string; size: number; modified_at: number; }
export interface GitDiffResult { diff: string; status: string[]; }
export interface TerminalResult { command: string; stdout: string; stderr: string; exit_code: number; }
export interface HeadroomStats { available: boolean; tokens_saved: number; savings_percent: number; requests: number; }

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
  createProject(input: CreateProjectInput): Promise<{ project: Project }>;
  setDefaultProject(name: string): Promise<{ project: Project }>;
  updateProject(input: UpdateProjectInput): Promise<{ project: Project; old_path: string; moved: boolean }>;
  removeProject(name: string): Promise<{ project: Project }>;
  getToolStatus(): Promise<{ tools: ToolStatus[] }>;
  bootstrapRuntime(): Promise<RuntimeStatus>;
  getRuntimeStatus(): Promise<RuntimeStatus>;
  updatePrivateTools(): Promise<{ tools: Array<{ key: string; status: string; detail: string }> }>;
  getCodexUsage(): Promise<CodexUsage>;
  copyText(text: string): Promise<{ copied: boolean }>;
  startChat(input: { task_id?: string; name: string; prompt: string; permission: "standard" | "full"; session_id?: string; images?: string[] }): Promise<{ task_id: string }>;
  saveClipboardImage(input: { data_url: string; name?: string }): Promise<{ path: string }>;
  stopChat(taskId: string): Promise<{ stopped: boolean }>;
  onChatEvent(callback: (event: ChatEvent) => void): () => void;
  getFileTree(name: string): Promise<{ items: FileTreeItem[]; truncated: boolean }>;
  readFile(name: string, path: string): Promise<{ path: string; content: string }>;
  getRecentImages(name: string, since: number, limit?: number): Promise<{ images: ImageArtifact[] }>;
  getImagePreview(name: string, path: string): Promise<{ data_url: string; width: number; height: number }>;
  getGitDiff(name: string, path?: string): Promise<GitDiffResult>;
  stageFile(name: string, path: string): Promise<{ path: string; status: string }>;
  restoreFile(name: string, path: string): Promise<{ path: string; status: string }>;
  runTerminal(name: string, command: string): Promise<TerminalResult>;
  getHeadroomStats(name: string, port?: number): Promise<HeadroomStats>;
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
