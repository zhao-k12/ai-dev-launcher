import { _electron as electron } from "playwright";
import { access, mkdtemp } from "node:fs/promises";
import { join, resolve } from "node:path";
import { tmpdir } from "node:os";

const root = resolve(import.meta.dirname, "../..");
const tempRoot = await mkdtemp(join(tmpdir(), "ai-dev-launcher-v2-e2e-"));
const configDir = join(tempRoot, "config");
const application = await electron.launch({ args: ["."], cwd: resolve(root, "desktop"), env: { ...process.env, AI_DEV_CONFIG_DIR: configDir, AI_DEV_PYTHON: resolve(root, ".venv/Scripts/python.exe"), AI_DEV_BRIDGE_TEST_MODE: "1" } });

try {
  const page = await application.firstWindow();
  await page.getByText("创建第一个项目").waitFor();
  await page.getByRole("button", { name: "创建新项目" }).click();
  await page.getByTestId("project-name").fill("sample-project");
  await page.getByTestId("project-path").evaluate((element, value) => { element.removeAttribute("readonly"); element.value = value; element.dispatchEvent(new Event("input", { bubbles: true })); }, tempRoot);
  await page.getByTestId("submit-project").click();
  await page.getByText("已创建并初始化").waitFor();
  await access(join(tempRoot, "sample-project", "AGENTS.md"));
  await access(join(tempRoot, "sample-project", ".ai-dev-launcher", "project.json"));
  await page.getByText("有什么可以帮你？").waitFor();
  await page.screenshot({ path: resolve(root, "design/v2-phase2-chat-workspace.png") });

  await page.getByTestId("environment-check").click();
  await page.getByText("进程级隔离 · 不修改 Codex 桌面端").waitFor();
  await page.getByRole("button", { name: "完成" }).click();
  await page.getByTestId("cli-version").click();
  await page.getByText("启动器私有 Codex CLI").waitFor();
  await page.getByText("不影响 Codex 桌面端和全局 CLI").waitFor();
  await page.screenshot({ path: resolve(root, "design/v2-phase1-implemented.png") });
} catch (error) {
  const page = await application.firstWindow();
  console.error("E2E PAGE TEXT:", await page.locator("body").innerText());
  await page.screenshot({ path: resolve(root, "design/v2-phase1-e2e-failure.png") });
  throw error;
} finally {
  await application.close();
}
