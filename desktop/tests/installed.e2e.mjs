import { _electron as electron } from "playwright";
import { access, mkdtemp } from "node:fs/promises";
import { join, resolve } from "node:path";
import { tmpdir } from "node:os";

const executablePath = process.env.AI_DEV_INSTALLED_EXE;
if (!executablePath) {
  throw new Error("AI_DEV_INSTALLED_EXE is required.");
}

const root = resolve(import.meta.dirname, "../..");
const tempRoot = await mkdtemp(join(tmpdir(), "ai-dev-launcher-installed-"));
const projectDir = join(tempRoot, "installed-project");

const application = await electron.launch({
  executablePath,
  env: {
    ...process.env,
    AI_DEV_CONFIG_DIR: join(tempRoot, "config"),
    AI_DEV_BRIDGE_TEST_MODE: "1",
    AI_DEV_PYTHON: ""
  }
});

try {
  const page = await application.firstWindow();
  const chromeState = await application.evaluate(({ BrowserWindow, Menu }) => ({
    title: BrowserWindow.getAllWindows()[0]?.getTitle(),
    hasMenu: Menu.getApplicationMenu() !== null
  }));
  if (chromeState.title !== "AI Dev Launcher v2.0.6") throw new Error(`Unexpected window title: ${chromeState.title}`);
  if (chromeState.hasMenu) throw new Error("Application menu should be hidden");
  await page.getByRole("button", { name: "创建新项目" }).click();
  await page.getByTestId("project-name").fill("installed-project");
  await page.getByTestId("project-path").evaluate((element, value) => {
    element.removeAttribute("readonly");
    element.value = value;
    element.dispatchEvent(new Event("input", { bubbles: true }));
  }, tempRoot);
  await page.getByTestId("submit-project").click();
  await page.getByText(projectDir).first().waitFor();

  await page.getByTestId("environment-check").click();
  await page.getByText("进程级隔离 · 不修改 Codex 桌面端").waitFor();
  await page.getByText("Codex 桌面端配置独立").waitFor();
  await page.getByRole("button", { name: "完成" }).click();
  await access(join(projectDir, "AGENTS.md"));
  await access(join(projectDir, ".ai-dev-launcher", "project.json"));


  await page.screenshot({
    path: resolve(root, "design/gui-installed.png")
  });
} catch (error) {
  const page = await application.firstWindow();
  console.error("INSTALLED PAGE URL:", page.url());
  console.error("INSTALLED PAGE TEXT:", await page.locator("body").innerText());
  await page.screenshot({
    path: resolve(root, "design/gui-installed-failure.png")
  });
  throw error;
} finally {
  await application.close();
}
