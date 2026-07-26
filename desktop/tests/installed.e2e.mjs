import { _electron as electron } from "playwright";
import { access, mkdtemp, mkdir } from "node:fs/promises";
import { join, resolve } from "node:path";
import { tmpdir } from "node:os";

const executablePath = process.env.AI_DEV_INSTALLED_EXE;
if (!executablePath) {
  throw new Error("AI_DEV_INSTALLED_EXE is required.");
}

const root = resolve(import.meta.dirname, "../..");
const tempRoot = await mkdtemp(join(tmpdir(), "ai-dev-launcher-installed-"));
const projectDir = join(tempRoot, "installed-project");
await mkdir(projectDir, { recursive: true });

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
  await page.getByRole("button", { name: /添加第一个项目|娣诲姞绗竴涓」鐩?/ }).click();
  await page.getByTestId("project-name").fill("installed-project");
  await page.getByTestId("project-path").fill(projectDir);
  await page.getByTestId("submit-project").click();
  await page.getByText(projectDir).first().waitFor();

  await page.getByTestId("environment-check").click();
  await page.getByText("Codex", { exact: true }).waitFor();
  await page.locator("button").filter({ hasText: /^(关闭|鍏抽棴)$/ }).click();

  await page.getByTestId("initialize-project").click();
  await page.getByTestId("preview-prepare").click();
  await page.getByTestId("apply-prepare").click();
  await page.getByTestId("prepare-complete").waitFor();
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
