import { _electron as electron } from "playwright";
import { access, mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { tmpdir } from "node:os";

const root = resolve(import.meta.dirname, "../..");
const tempRoot = await mkdtemp(join(tmpdir(), "ai-dev-launcher-v2-e2e-"));
const configDir = join(tempRoot, "config");
const movedParent = join(tempRoot, "moved-projects");
await mkdir(movedParent);
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
  const keyframeDir = join(tempRoot, "sample-project", "关键帧");
  await mkdir(keyframeDir);
  await writeFile(join(keyframeDir, "S01.png"), Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=", "base64"));
  const imagePreview = await page.evaluate(async () => {
    const images = await window.launcher.getRecentImages("sample-project", 0, 4);
    return images.images.length ? window.launcher.getImagePreview("sample-project", images.images[0].path) : null;
  });
  if (!imagePreview?.data_url.startsWith("data:image/jpeg;base64,")) throw new Error("Generated image preview is unavailable");
  await page.getByText("有什么可以帮你？").waitFor();
  await page.getByTestId("project-row-sample-project").click({ button: "right" });
  await page.getByRole("button", { name: "编辑项目" }).click();
  await page.getByRole("heading", { name: "编辑项目" }).waitFor();
  await page.getByTestId("edit-project-name").fill("sample-renamed");
  await page.getByTestId("edit-project-parent").evaluate((element, value) => { element.removeAttribute("readonly"); element.value = value; element.dispatchEvent(new Event("input", { bubbles: true })); }, movedParent);
  await page.getByTestId("save-project").click();
  await page.getByText("已保存并移动到新位置").waitFor();
  await access(join(movedParent, "sample-project", "AGENTS.md"));
  try {
    await access(join(tempRoot, "sample-project"));
    throw new Error("Original project directory still exists after moving");
  } catch (error) {
    if (error?.message === "Original project directory still exists after moving") throw error;
  }
  await page.getByTestId("add-project").click();
  await page.getByTestId("project-name").fill("中欧视频-2026");
  await page.getByTestId("project-path").evaluate((element, value) => { element.removeAttribute("readonly"); element.value = value; element.dispatchEvent(new Event("input", { bubbles: true })); }, tempRoot);
  await page.getByTestId("submit-project").click();
  await page.getByText("“中欧视频-2026”已创建并初始化。").waitFor();
  await access(join(tempRoot, "中欧视频-2026", "AGENTS.md"));
  await page.evaluate(({ key }) => {
    const messages = Array.from({ length: 80 }, (_, index) => ({
      id: `history-${index}`,
      role: index % 2 ? "assistant" : "user",
      text: `${index}: ${"long historical message ".repeat(12)}`
    }));
    localStorage.setItem(key, JSON.stringify([{ id: "history", name: "history", updatedAt: new Date().toISOString(), messages }]));
  }, { key: `ai-dev-launcher:sessions:${join(movedParent, "sample-project")}` });
  await page.getByTestId("project-row-sample-renamed").click();
  await page.waitForTimeout(300);
  const latestMessageVisible = await page.getByTestId("message-list").evaluate((element) =>
    element.scrollHeight - element.clientHeight - element.scrollTop <= 2
  );
  if (!latestMessageVisible) throw new Error("Project history did not open at the latest message");
  const chatLayout = await page.evaluate(() => ({
    composerPosition: getComputedStyle(document.querySelector(".composer-shell")).position,
    horizontalOverflow: getComputedStyle(document.querySelector(".message-list")).overflowX
  }));
  if (chatLayout.composerPosition !== "absolute") throw new Error(`Composer is not floating: ${chatLayout.composerPosition}`);
  if (chatLayout.horizontalOverflow !== "hidden") throw new Error(`Message list can scroll horizontally: ${chatLayout.horizontalOverflow}`);
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
