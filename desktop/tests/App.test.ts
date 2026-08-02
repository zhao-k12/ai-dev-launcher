import { createApp, nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../src/App.vue";
import type { ChatEvent } from "../src/types";

const project = { name: "my-app", path: "D:\\Projects\\my-app", created_at: "2026-01-01T00:00:00Z" };
const runtime = {
  status: "ready" as const,
  checks: [
    { key: "codex_config", label: "Codex 桌面端配置独立", status: "ready" as const, detail: "启动器未修改全局 Codex 配置" },
    { key: "headroom", label: "Headroom 已就绪", status: "ready" as const, detail: null },
    { key: "codex", label: "Codex CLI 可用", status: "ready" as const, detail: null },
    { key: "recovery", label: "未发现异常退出残留", status: "ready" as const, detail: null }
  ],
  headroom_version: "headroom 2.0",
  codex_version: "codex 2.0",
  headroom_port: null,
  isolation: "process" as const,
  automatic_updates: true,
  last_checked: "2026-01-01T00:00:00Z"
};
let chatListener: ((event: ChatEvent) => void) | undefined;

async function flush(): Promise<void> { await Promise.resolve(); await new Promise((resolve) => setTimeout(resolve, 0)); await nextTick(); }
async function render() { const host = document.createElement("div"); document.body.append(host); const application = createApp(App); application.mount(host); await flush(); return { host, unmount() { application.unmount(); host.remove(); } }; }
function clickButton(host: HTMLElement, label: string): void { const button = [...host.querySelectorAll("button")].find((item) => item.textContent?.includes(label)); if (!button) throw new Error(`Button not found: ${label}`); button.click(); }
function setInput(element: HTMLInputElement, value: string): void { element.value = value; element.dispatchEvent(new Event("input", { bubbles: true })); }

describe("App v2 Phase 1", () => {
  beforeEach(() => {
    vi.clearAllMocks(); document.body.innerHTML = ""; localStorage.clear();
    vi.mocked(window.launcher.listProjects).mockResolvedValue({ projects: [], default_project: null });
    vi.mocked(window.launcher.bootstrapRuntime).mockResolvedValue(runtime);
    vi.mocked(window.launcher.getRuntimeStatus).mockResolvedValue(runtime);
    vi.mocked(window.launcher.updatePrivateTools).mockResolvedValue({ tools: [] });
    vi.mocked(window.launcher.getCodexUsage).mockResolvedValue({ available: true, used_percent: 17, remaining_percent: 83, resets_at: 1786175808, window_minutes: 10080, plan_type: "plus" });
    vi.mocked(window.launcher.onChatEvent).mockImplementation((callback) => { chatListener = callback; return () => undefined; });
    vi.mocked(window.launcher.getFileTree).mockResolvedValue({ items: [], truncated: false });
    vi.mocked(window.launcher.getGitDiff).mockResolvedValue({ diff: "", status: [] });
    vi.mocked(window.launcher.getHeadroomStats).mockResolvedValue({ available: true, tokens_saved: 1200, savings_percent: 12, requests: 4 });
    vi.mocked(window.launcher.runTerminal).mockResolvedValue({ command: "pwd", stdout: "D:\\Projects\\my-app", stderr: "", exit_code: 0 });
    vi.mocked(window.launcher.launchProject).mockResolvedValue({ pid: 1234 });
  });

  it("offers zero-configuration project creation", async () => {
    const view = await render();
    expect(view.host.textContent).toContain("创建第一个项目");
    expect(view.host.textContent).toContain("其余工作将自动完成");
    view.unmount();
  });

  it("shows the integrated conversation workspace", async () => {
    vi.mocked(window.launcher.listProjects).mockResolvedValue({ projects: [project], default_project: "my-app" });
    const view = await render();
    expect(view.host.textContent).toContain("与 Codex 桌面端独立");
    expect(view.host.textContent).toContain("Codex 剩余 83%");
    expect(view.host.textContent).toContain("有什么可以帮你？");
    expect(view.host.textContent).toContain("标准模式");
    view.unmount();
  });

  it("opens a project at the latest conversation message after layout settles", async () => {
    vi.mocked(window.launcher.listProjects).mockResolvedValue({ projects: [project], default_project: project.name });
    localStorage.setItem(`ai-dev-launcher:sessions:${project.path}`, JSON.stringify([{
      id: "session-latest", name: "历史会话", updatedAt: new Date().toISOString(),
      messages: [
        { id: "old", role: "user", text: "第一行" },
        { id: "latest", role: "assistant", text: "最新消息" }
      ]
    }]));
    const view = await render();
    const list = view.host.querySelector('[data-testid="message-list"]') as HTMLElement;
    Object.defineProperty(list, "scrollHeight", { configurable: true, value: 900 });
    list.scrollTop = 0;
    await new Promise((resolve) => window.setTimeout(resolve, 200));
    expect(list.scrollTop).toBe(900);
    expect(view.host.textContent).toContain("最新消息");
    view.unmount();
  });

  it("automatically starts a fresh Codex topic after the history threshold", async () => {
    vi.mocked(window.launcher.listProjects).mockResolvedValue({ projects: [project], default_project: project.name });
    vi.mocked(window.launcher.startChat).mockResolvedValue({ task_id: "task-rotate" });
    localStorage.setItem(`ai-dev-launcher:sessions:${project.path}`, JSON.stringify([{
      id: "session-1", codexSessionId: "old-codex-thread", name: "长期任务", updatedAt: new Date().toISOString(),
      turnCount: 40, lastInputTokens: 170_000,
      messages: Array.from({ length: 40 }, (_, index) => ({ id: `user-${index}`, role: "user", text: `消息 ${index}` }))
    }]));
    const view = await render();
    setInput(view.host.querySelector('[data-testid="chat-prompt"]') as HTMLInputElement, "继续完成修改"); await nextTick();
    clickButton(view.host, "发送"); await flush();
    expect(window.launcher.startChat).toHaveBeenCalledWith(expect.objectContaining({ session_id: undefined, prompt: expect.stringContaining("用户最新消息：\n继续完成修改") }));
    expect(vi.mocked(window.launcher.startChat).mock.calls[0][0].prompt).toContain("消息 39");
    expect(view.host.textContent).toContain("已自动续接到新会话");
    view.unmount();
  });

  it("does not rotate again just because retained UI history is long", async () => {
    vi.mocked(window.launcher.listProjects).mockResolvedValue({ projects: [project], default_project: project.name });
    vi.mocked(window.launcher.startChat).mockResolvedValue({ task_id: "task-continue" });
    localStorage.setItem(`ai-dev-launcher:sessions:${project.path}`, JSON.stringify([{
      id: "session-1", codexSessionId: "current-codex-thread", name: "长期任务", updatedAt: new Date().toISOString(),
      turnCount: 1, lastInputTokens: 12_000, topicChars: 200,
      messages: Array.from({ length: 80 }, (_, index) => ({ id: `old-${index}`, role: index % 2 ? "assistant" : "user", text: "旧界面记录".repeat(200) }))
    }]));
    const view = await render();
    setInput(view.host.querySelector('[data-testid="chat-prompt"]') as HTMLInputElement, "开发"); await nextTick();
    clickButton(view.host, "发送"); await flush();
    expect(window.launcher.startChat).toHaveBeenCalledWith(expect.objectContaining({ session_id: "current-codex-thread", prompt: "开发" }));
    expect(view.host.textContent).not.toContain("自动续接到新会话");
    view.unmount();
  });

  it("submits an approved implementation plan for direct execution", async () => {
    vi.mocked(window.launcher.listProjects).mockResolvedValue({ projects: [project], default_project: project.name });
    vi.mocked(window.launcher.startChat).mockResolvedValue({ task_id: "task-plan" });
    const plan = `实施计划\n\n阶段一：修改文件\n${"完成模块实现和自动测试。".repeat(30)}\n\n验收标准：测试全部通过。`;
    const view = await render();
    setInput(view.host.querySelector('[data-testid="chat-prompt"]') as HTMLInputElement, plan); await nextTick();
    clickButton(view.host, "发送"); await flush();
    expect(window.launcher.startChat).toHaveBeenCalledWith(expect.objectContaining({ prompt: expect.stringContaining("直接实施") }));
    expect(vi.mocked(window.launcher.startChat).mock.calls[0][0].prompt).toContain(plan);
    expect(view.host.textContent).toContain("不再重新制定计划");
    view.unmount();
  });

  it("creates a project from a name and parent location", async () => {
    vi.mocked(window.launcher.createProject).mockResolvedValue({ project });
    vi.mocked(window.launcher.listProjects).mockResolvedValueOnce({ projects: [], default_project: null }).mockResolvedValueOnce({ projects: [project], default_project: "my-app" });
    const view = await render();
    clickButton(view.host, "创建新项目"); await nextTick();
    setInput(view.host.querySelector('[data-testid="project-name"]') as HTMLInputElement, "my-app");
    const path = view.host.querySelector('[data-testid="project-path"]') as HTMLInputElement;
    path.removeAttribute("readonly"); setInput(path, "D:\\Projects");
    clickButton(view.host, "创建并进入"); await flush();
    expect(window.launcher.createProject).toHaveBeenCalledWith({ name: "my-app", parent: "D:\\Projects" });
    expect(view.host.textContent).toContain("已创建并初始化");
    view.unmount();
  });

  it("keeps environment status read-only", async () => {
    const view = await render(); clickButton(view.host, "环境状态"); await nextTick();
    expect(view.host.textContent).toContain("所有恢复和隔离操作均由启动器自动完成");
    expect(view.host.textContent).not.toContain("修改配置");
    view.unmount();
  });

  it("labels automatic updates as launcher-private", async () => {
    const view = await render(); clickButton(view.host, "CLI 版本"); await nextTick();
    expect(view.host.textContent).toContain("启动器私有 Codex CLI");
    expect(view.host.textContent).toContain("自动更新");
    expect(view.host.textContent).toContain("不影响 Codex 桌面端和全局 CLI");
    view.unmount();
  });

  it("starts and stops an integrated Codex task", async () => {
    vi.mocked(window.launcher.listProjects).mockResolvedValue({ projects: [project], default_project: "my-app" });
    vi.mocked(window.launcher.startChat).mockResolvedValue({ task_id: "task-1" });
    vi.mocked(window.launcher.stopChat).mockResolvedValue({ stopped: true });
    const view = await render();
    setInput(view.host.querySelector('[data-testid="chat-prompt"]') as HTMLInputElement, "修复测试");
    await nextTick();
    clickButton(view.host, "发送"); await flush();
    expect(window.launcher.startChat).toHaveBeenCalledWith(expect.objectContaining({ name: "my-app", prompt: "修复测试", permission: "standard", session_id: undefined }));
    const taskId = vi.mocked(window.launcher.startChat).mock.calls[0][0].task_id!;
    clickButton(view.host, "停止"); await flush();
    expect(window.launcher.stopChat).toHaveBeenCalledWith(taskId);
    chatListener?.({ task_id: taskId, type: "complete", exit_code: 1, cancelled: true });
    await nextTick();
    expect(view.host.textContent).not.toContain("Codex 已退出，代码 1");
    expect(view.host.querySelector(".chat-error")).toBeNull();
    view.unmount();
  });

  it("keeps the active project selected while its Codex task is running", async () => {
    const other = { ...project, name: "other-app", path: "D:\\Projects\\other-app" };
    vi.mocked(window.launcher.listProjects).mockResolvedValue({ projects: [project, other], default_project: project.name });
    vi.mocked(window.launcher.startChat).mockImplementation(async (input) => ({ task_id: input.task_id! }));
    const view = await render();
    setInput(view.host.querySelector('[data-testid="chat-prompt"]') as HTMLInputElement, "执行任务");
    await nextTick();
    clickButton(view.host, "发送"); await flush();
    (view.host.querySelector('[data-testid="project-row-other-app"]') as HTMLButtonElement).click();
    await flush();
    expect(view.host.querySelector('[data-testid="project-row-my-app"]')?.classList.contains("selected")).toBe(true);
    expect(view.host.textContent).toContain("请等待当前任务完成或先停止任务");
    view.unmount();
  });

  it("renders Codex JSON events and saves the resumable session", async () => {
    vi.mocked(window.launcher.listProjects).mockResolvedValue({ projects: [project], default_project: "my-app" });
    vi.mocked(window.launcher.startChat).mockImplementation(async (input) => ({ task_id: input.task_id! }));
    const view = await render();
    setInput(view.host.querySelector('[data-testid="chat-prompt"]') as HTMLInputElement, "解释项目"); await nextTick();
    clickButton(view.host, "发送"); await flush();
    const input = vi.mocked(window.launcher.startChat).mock.calls[0][0];
    chatListener?.({ task_id: input.task_id!, type: "codex", event: { type: "thread.started", thread_id: "thread-1" } });
    chatListener?.({ task_id: input.task_id!, type: "codex", event: { type: "turn.started" } });
    chatListener?.({ task_id: input.task_id!, type: "codex", event: { type: "item.completed", item: { type: "agent_message", text: "这是项目说明。" } } });
    chatListener?.({ task_id: input.task_id!, type: "complete", exit_code: 0 });
    await nextTick();
    expect(view.host.textContent).toContain("这是项目说明。");
    expect(view.host.textContent).not.toContain("Codex 正在思考");
    expect(localStorage.getItem(`ai-dev-launcher:sessions:${project.path}`)).not.toContain('"role":"status"');
    view.unmount();
  });

  it("collapses tool and code output by default", async () => {
    vi.mocked(window.launcher.listProjects).mockResolvedValue({ projects: [project], default_project: "my-app" });
    localStorage.setItem(`ai-dev-launcher:sessions:${project.path}`, JSON.stringify([{
      id: "session-1", name: "test", updatedAt: new Date().toISOString(),
      messages: [{ id: "tool-1", role: "tool", text: "large code output" }]
    }]));
    const view = await render();
    const details = view.host.querySelector("details.tool-details") as HTMLDetailsElement;
    expect(details).not.toBeNull();
    expect(details.open).toBe(false);
    expect(details.querySelector("summary")?.textContent).toContain("点击查看");
    view.unmount();
  });

  it("groups tool details for one turn and becomes idle on turn completion", async () => {
    vi.mocked(window.launcher.listProjects).mockResolvedValue({ projects: [project], default_project: project.name });
    vi.mocked(window.launcher.startChat).mockImplementation(async (input) => ({ task_id: input.task_id! }));
    vi.mocked(window.launcher.stopChat).mockResolvedValue({ stopped: true });
    const view = await render();
    setInput(view.host.querySelector('[data-testid="chat-prompt"]') as HTMLInputElement, "执行修改"); await nextTick();
    clickButton(view.host, "发送"); await flush();
    const taskId = vi.mocked(window.launcher.startChat).mock.calls[0][0].task_id!;
    const storageWrite = vi.spyOn(Storage.prototype, "setItem");
    storageWrite.mockClear();
    chatListener?.({ task_id: taskId, type: "codex", event: { type: "item.completed", item: { type: "command_execution", command: "test one", aggregated_output: "one" } } });
    chatListener?.({ task_id: taskId, type: "codex", event: { type: "item.completed", item: { type: "command_execution", command: "test two", aggregated_output: "two" } } });
    chatListener?.({ task_id: taskId, type: "codex", event: { type: "turn.completed", usage: { input_tokens: 1000 } } });
    await flush();
    expect(view.host.querySelectorAll("details.tool-details")).toHaveLength(1);
    expect(view.host.querySelector("details.tool-details")?.textContent).toContain("test one");
    expect(view.host.querySelector("details.tool-details")?.textContent).toContain("test two");
    expect(view.host.querySelector('[data-testid="stop-chat"]')).toBeNull();
    expect(view.host.querySelector('[data-testid="send-chat"]')).not.toBeNull();
    expect(window.launcher.stopChat).toHaveBeenCalledWith(taskId);
    expect(storageWrite).toHaveBeenCalledTimes(1);
    storageWrite.mockRestore();
    view.unmount();
  });

  it("renders assistant markdown and collapses fenced code", async () => {
    vi.mocked(window.launcher.listProjects).mockResolvedValue({ projects: [project], default_project: "my-app" });
    vi.mocked(window.launcher.copyText).mockResolvedValue({ copied: true });
    vi.mocked(window.launcher.openLink).mockResolvedValue({ opened: true });
    localStorage.setItem(`ai-dev-launcher:sessions:${project.path}`, JSON.stringify([{
      id: "session-1", name: "test", updatedAt: new Date().toISOString(),
      messages: [{ id: "answer-1", role: "assistant", text: "## 结果\n\n[打开页面](index.html)\n\n```ts\nconst ready = true;\n```" }]
    }]));
    const view = await render();
    expect(view.host.querySelector(".markdown-body h2")?.textContent).toBe("结果");
    const details = view.host.querySelector("details.inline-code-details") as HTMLDetailsElement;
    expect(details.open).toBe(false);
    expect(details.textContent).toContain("TypeScript");
    (details.querySelector("button.copy-action") as HTMLButtonElement).click();
    await flush();
    expect(window.launcher.copyText).toHaveBeenCalledWith("const ready = true;");
    (view.host.querySelector(".message-actions button") as HTMLButtonElement).click();
    await flush();
    expect(window.launcher.copyText).toHaveBeenLastCalledWith(expect.stringContaining("const ready = true;"));
    (view.host.querySelector('.markdown-body a[href="index.html"]') as HTMLAnchorElement).click();
    await flush();
    expect(window.launcher.openLink).toHaveBeenCalledWith(project.name, "index.html");
    view.unmount();
  });

  it("shows images generated during a completed task", async () => {
    vi.mocked(window.launcher.listProjects).mockResolvedValue({ projects: [project], default_project: project.name });
    vi.mocked(window.launcher.startChat).mockImplementation(async (input) => ({ task_id: input.task_id! }));
    vi.mocked(window.launcher.getRecentImages).mockResolvedValue({ images: [{ path: "关键帧/S01.png", name: "S01.png", size: 100, modified_at: Date.now() / 1000 }] });
    vi.mocked(window.launcher.getImagePreviews).mockResolvedValue({ previews: { "关键帧/S01.png": "data:image/png;base64,iVBORw0KGgo=" } });
    const view = await render();
    setInput(view.host.querySelector('[data-testid="chat-prompt"]') as HTMLInputElement, "生成图片"); await nextTick();
    clickButton(view.host, "发送"); await flush();
    const input = vi.mocked(window.launcher.startChat).mock.calls[0][0];
    chatListener?.({ task_id: input.task_id!, type: "codex", event: { type: "item.completed", item: { type: "agent_message", text: "图片已生成。" } } });
    chatListener?.({ task_id: input.task_id!, type: "complete", exit_code: 0 });
    await vi.waitFor(() => expect(view.host.querySelector(".artifact-gallery img")).not.toBeNull());
    expect(window.launcher.getImagePreviews).toHaveBeenCalledTimes(1);
    expect(window.launcher.getImagePreview).not.toHaveBeenCalled();
    (view.host.querySelector(".artifact-grid button") as HTMLButtonElement).click(); await nextTick();
    expect(view.host.querySelector(".image-lightbox")).not.toBeNull();
    view.unmount();
  });

  it("does not attach historical images when reopening a conversation", async () => {
    vi.mocked(window.launcher.listProjects).mockResolvedValue({ projects: [project], default_project: project.name });
    localStorage.setItem(`ai-dev-launcher:sessions:${project.path}`, JSON.stringify([{
      id: "session-1", name: "历史会话", updatedAt: new Date().toISOString(),
      messages: [{ id: "answer-1", role: "assistant", text: "图片已经生成在关键帧目录。" }]
    }]));
    const view = await render();
    expect(window.launcher.getRecentImages).not.toHaveBeenCalled();
    expect(view.host.querySelector(".artifact-gallery")).toBeNull();
    view.unmount();
  });

  it("accepts a pasted image", async () => {
    vi.mocked(window.launcher.listProjects).mockResolvedValue({ projects: [project], default_project: "my-app" });
    vi.mocked(window.launcher.saveClipboardImage).mockResolvedValue({ path: "C:\\temp\\image.png" });
    const view = await render();
    const file = new File([new Uint8Array([1, 2, 3])], "image.png", { type: "image/png" });
    const event = new Event("paste", { bubbles: true, cancelable: true });
    Object.defineProperty(event, "clipboardData", { value: { files: [file] } });
    view.host.querySelector('[data-testid="chat-prompt"]')?.dispatchEvent(event);
    await vi.waitFor(() => expect(window.launcher.saveClipboardImage).toHaveBeenCalledOnce());
    await flush();
    expect(view.host.querySelector(".composer-images img")).not.toBeNull();
    vi.mocked(window.launcher.startChat).mockResolvedValue({ task_id: "task-image" });
    clickButton(view.host, "发送"); await flush();
    expect(view.host.querySelector(".message-upload-images img")).not.toBeNull();
    view.unmount();
  });

  it("opens project actions with right click and sets the default", async () => {
    vi.mocked(window.launcher.listProjects).mockResolvedValue({ projects: [project], default_project: null });
    vi.mocked(window.launcher.setDefaultProject).mockResolvedValue({ project });
    const view = await render();
    view.host.querySelector(`[data-testid="project-row-${project.name}"]`)?.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, clientX: 30, clientY: 80 }));
    await nextTick();
    clickButton(view.host, "设为默认"); await flush();
    expect(window.launcher.setDefaultProject).toHaveBeenCalledWith(project.name);
    view.unmount();
  });

  it("edits a project from the right-click menu", async () => {
    vi.mocked(window.launcher.listProjects).mockResolvedValue({ projects: [project], default_project: project.name });
    vi.mocked(window.launcher.updateProject).mockResolvedValue({ project: { ...project, name: "renamed" }, old_path: project.path, moved: false });
    const view = await render();
    view.host.querySelector(`[data-testid="project-row-${project.name}"]`)?.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, clientX: 30, clientY: 80 }));
    await nextTick();
    clickButton(view.host, "编辑项目"); await nextTick();
    setInput(view.host.querySelector('[data-testid="edit-project-name"]') as HTMLInputElement, "renamed");
    clickButton(view.host, "保存更改"); await flush();
    expect(window.launcher.updateProject).toHaveBeenCalledWith(expect.objectContaining({ current_name: project.name, name: "renamed" }));
    view.unmount();
  });

});
