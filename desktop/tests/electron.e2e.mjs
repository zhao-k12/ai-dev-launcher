import { _electron as electron } from "playwright";
import { access, mkdtemp, mkdir } from "node:fs/promises";
import { join, resolve } from "node:path";
import { tmpdir } from "node:os";

const root = resolve(import.meta.dirname, "../..");
const tempRoot = await mkdtemp(join(tmpdir(), "ai-dev-launcher-e2e-"));
const configDir = join(tempRoot, "config");
const projectDir = join(tempRoot, "sample-project");
const secondProjectDir = join(tempRoot, "second-project");
await mkdir(projectDir, { recursive: true });
await mkdir(secondProjectDir, { recursive: true });

const application = await electron.launch({
  args: ["."],
  cwd: resolve(root, "desktop"),
  env: {
    ...process.env,
    AI_DEV_CONFIG_DIR: configDir,
    AI_DEV_PYTHON: resolve(root, ".venv/Scripts/python.exe"),
    AI_DEV_BRIDGE_TEST_MODE: "1"
  }
});

try {
  const page = await application.firstWindow();
  await page.getByText("尚未添加项目").waitFor();
  await page.getByRole("button", { name: "添加第一个项目" }).click();
  await page.getByTestId("project-name").fill("sample-project");
  await page.getByTestId("project-path").fill(projectDir);
  await page.getByTestId("submit-project").click();
  await page.getByText("项目添加成功。").waitFor();
  await page.getByText(projectDir).first().waitFor();
  await page.getByTestId("environment-check").click();
  await page.getByText("开发环境检查").waitFor();
  await page.getByText("Codex", { exact: true }).waitFor();
  await page.screenshot({ path: resolve(root, "design/gui-phase2-implemented.png") });
  await page.getByRole("button", { name: "关闭", exact: true }).click();
  await page.getByTestId("launch-codex").click();
  await page.getByText("新终端窗口启动", { exact: false }).waitFor();
  await page.getByTestId("initialize-project").click();
  await page.getByTestId("preview-prepare").click();
  await page.getByText("Dry run", { exact: false }).waitFor();
  await page.screenshot({ path: resolve(root, "design/gui-phase3-implemented.png") });
  await page.getByTestId("apply-prepare").click();
  await page.getByTestId("prepare-complete").waitFor();
  await access(join(projectDir, "AGENTS.md"));
  await access(join(projectDir, ".ai-dev-launcher", "project.json"));
  await access(join(projectDir, ".git"));
  await page.getByTestId("finish-prepare").click();

  await page.getByTestId("add-project").click();
  await page.getByTestId("project-name").fill("second-project");
  await page.getByTestId("project-path").fill(secondProjectDir);
  await page.getByTestId("submit-project").click();
  await page.getByTestId("project-row-second-project").click();
  await page.getByTestId("make-default").click();
  await page.getByText("默认项目已更新。").waitFor();
  await page.getByTestId("remove-project").click();
  await page.getByTestId("confirm-remove").click();
  await page.getByText("项目文件未删除。", { exact: false }).waitFor();
  await page.getByTestId("project-row-second-project").waitFor({
    state: "detached"
  });
} catch (error) {
  const page = await application.firstWindow();
  console.error("E2E PAGE TEXT:", await page.locator("body").innerText());
  await page.screenshot({
    path: resolve(root, "design/gui-phase1-e2e-failure.png")
  });
  throw error;
} finally {
  await application.close();
}
