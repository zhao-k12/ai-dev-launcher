import { createApp, nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../src/App.vue";

const project = {
  name: "my-app",
  path: "D:\\Projects\\my-app",
  created_at: "2026-01-01T00:00:00Z"
};
const tools = [
  {
    key: "codex",
    display_name: "Codex",
    status: "available" as const,
    required: true,
    command: "codex",
    path: "C:\\bin\\codex.cmd",
    version: "codex 1.0",
    detail: null,
    install_hint: null
  },
  {
    key: "headroom",
    display_name: "Headroom",
    status: "available" as const,
    required: true,
    command: "headroom",
    path: "C:\\bin\\headroom.exe",
    version: "headroom 1.0",
    detail: null,
    install_hint: null
  }
];

async function flush(): Promise<void> {
  await Promise.resolve();
  await new Promise((resolve) => setTimeout(resolve, 0));
  await nextTick();
}

async function render() {
  const host = document.createElement("div");
  document.body.append(host);
  const application = createApp(App);
  application.mount(host);
  await flush();
  return {
    host,
    unmount() {
      application.unmount();
      host.remove();
    }
  };
}

function clickButton(host: HTMLElement, label: string): void {
  const button = [...host.querySelectorAll("button")].find((candidate) =>
    candidate.textContent?.includes(label)
  );
  if (!button) throw new Error(`Button not found: ${label}`);
  button.click();
}

function setInput(element: HTMLInputElement, value: string): void {
  element.value = value;
  element.dispatchEvent(new Event("input", { bubbles: true }));
}

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = "";
    vi.mocked(window.launcher.listProjects).mockResolvedValue({
      projects: [],
      default_project: null
    });
    vi.mocked(window.launcher.getToolStatus).mockResolvedValue({ tools });
    vi.mocked(window.launcher.launchProject).mockResolvedValue({ pid: 1234 });
    vi.mocked(window.launcher.prepareProject).mockResolvedValue({
      project: "my-app",
      dry_run: true,
      actions: [
        {
          kind: "agents",
          target: "D:\\Projects\\my-app\\AGENTS.md",
          status: "planned",
          detail: "Create or update the managed AGENTS.md block"
        }
      ]
    });
  });

  it("shows the empty state", async () => {
    const view = await render();
    expect(
      view.host.querySelector('[data-testid="empty-state"]')?.textContent
    ).toContain("尚未添加项目");
    view.unmount();
  });

  it("renders projects and default state", async () => {
    vi.mocked(window.launcher.listProjects).mockResolvedValue({
      projects: [project],
      default_project: "my-app"
    });
    const view = await render();
    expect(view.host.textContent).toContain("my-app");
    expect(view.host.textContent).toContain("当前默认项目");
    expect(view.host.textContent).toContain("启动 Codex");
    view.unmount();
  });

  it("adds a project from the dialog", async () => {
    vi.mocked(window.launcher.addProject).mockResolvedValue({ project });
    vi.mocked(window.launcher.listProjects)
      .mockResolvedValueOnce({ projects: [], default_project: null })
      .mockResolvedValueOnce({
        projects: [project],
        default_project: "my-app"
      });
    const view = await render();

    clickButton(view.host, "添加第一个项目");
    await nextTick();
    setInput(
      view.host.querySelector(
        '[data-testid="project-name"]'
      ) as HTMLInputElement,
      "my-app"
    );
    setInput(
      view.host.querySelector(
        '[data-testid="project-path"]'
      ) as HTMLInputElement,
      "D:\\Projects\\my-app"
    );
    (
      view.host.querySelector(
        '[data-testid="submit-project"]'
      ) as HTMLButtonElement
    ).click();
    await flush();

    expect(window.launcher.addProject).toHaveBeenCalledWith({
      name: "my-app",
      path: "D:\\Projects\\my-app",
      make_default: false
    });
    expect(view.host.textContent).toContain("项目添加成功");
    view.unmount();
  });

  it("shows tool status and launches Codex", async () => {
    vi.mocked(window.launcher.listProjects).mockResolvedValue({
      projects: [project],
      default_project: "my-app"
    });
    const view = await render();

    clickButton(view.host, "启动 Codex");
    await flush();

    expect(window.launcher.launchProject).toHaveBeenCalledWith("my-app");
    expect(view.host.textContent).toContain("新终端窗口启动");

    clickButton(view.host, "环境检查");
    await nextTick();
    expect(view.host.textContent).toContain("开发环境检查");
    expect(view.host.textContent).toContain("codex 1.0");
    view.unmount();
  });

  it("previews and applies project initialization", async () => {
    vi.mocked(window.launcher.listProjects).mockResolvedValue({
      projects: [project],
      default_project: "my-app"
    });
    vi.mocked(window.launcher.prepareProject)
      .mockResolvedValueOnce({
        project: "my-app",
        dry_run: true,
        actions: [
          {
            kind: "agents",
            target: "D:\\Projects\\my-app\\AGENTS.md",
            status: "planned",
            detail: "Create AGENTS.md"
          }
        ]
      })
      .mockResolvedValueOnce({
        project: "my-app",
        dry_run: false,
        actions: [
          {
            kind: "agents",
            target: "D:\\Projects\\my-app\\AGENTS.md",
            status: "written",
            detail: "Create AGENTS.md"
          }
        ]
      });
    const view = await render();

    clickButton(view.host, "初始化项目");
    await nextTick();
    clickButton(view.host, "预览变更");
    await flush();
    expect(view.host.textContent).toContain("Dry run");

    clickButton(view.host, "执行初始化");
    await flush();
    expect(
      view.host.querySelector('[data-testid="prepare-complete"]')?.textContent
    ).toContain("项目初始化完成");
    expect(window.launcher.prepareProject).toHaveBeenCalledTimes(2);
    view.unmount();
  });
});
