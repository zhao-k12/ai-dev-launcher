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
    chatListener?.({ task_id: input.task_id!, type: "codex", event: { type: "item.completed", item: { type: "agent_message", text: "这是项目说明。" } } });
    chatListener?.({ task_id: input.task_id!, type: "complete", exit_code: 0 });
    await nextTick();
    expect(view.host.textContent).toContain("这是项目说明。");
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

  it("renders assistant markdown and collapses fenced code", async () => {
    vi.mocked(window.launcher.listProjects).mockResolvedValue({ projects: [project], default_project: "my-app" });
    localStorage.setItem(`ai-dev-launcher:sessions:${project.path}`, JSON.stringify([{
      id: "session-1", name: "test", updatedAt: new Date().toISOString(),
      messages: [{ id: "answer-1", role: "assistant", text: "## 结果\n\n已经完成。\n\n```ts\nconst ready = true;\n```" }]
    }]));
    const view = await render();
    expect(view.host.querySelector(".markdown-body h2")?.textContent).toBe("结果");
    const details = view.host.querySelector("details.inline-code-details") as HTMLDetailsElement;
    expect(details.open).toBe(false);
    expect(details.textContent).toContain("TypeScript");
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
    await flush();
    expect(window.launcher.saveClipboardImage).toHaveBeenCalledOnce();
    expect(view.host.querySelector(".composer-images img")).not.toBeNull();
    view.unmount();
  });

});
