<script setup lang="ts">
import { onMounted, ref } from "vue";
import AddProjectDialog from "./components/AddProjectDialog.vue";
import AppIcon from "./components/AppIcon.vue";
import CliVersionDialog from "./components/CliVersionDialog.vue";
import ChatWorkspace from "./components/ChatWorkspace.vue";
import EnvironmentDialog from "./components/EnvironmentDialog.vue";
import ProjectList from "./components/ProjectList.vue";
import type { CreateProjectInput, Project, RuntimeStatus } from "./types";

const projects = ref<Project[]>([]);
const defaultProject = ref<string | null>(null);
const selected = ref<Project | null>(null);
const runtime = ref<RuntimeStatus | null>(null);
const loading = ref(true);
const runtimeLoading = ref(true);
const busy = ref(false);
const error = ref("");
const notice = ref("");
const showCreate = ref(false);
const showEnvironment = ref(false);
const showVersions = ref(false);
const createDialog = ref<InstanceType<typeof AddProjectDialog> | null>(null);
function announce(message: string): void { notice.value = message; window.setTimeout(() => { if (notice.value === message) notice.value = ""; }, 4000); }

async function refresh(preferred?: string): Promise<void> {
  const result = await window.launcher.listProjects();
  projects.value = result.projects;
  defaultProject.value = result.default_project;
  selected.value = result.projects.find((item) => item.name === preferred) ?? result.projects.find((item) => item.name === result.default_project) ?? result.projects[0] ?? null;
}

async function refreshRuntime(bootstrap = false): Promise<void> {
  runtimeLoading.value = true;
  try { runtime.value = bootstrap ? await window.launcher.bootstrapRuntime() : await window.launcher.getRuntimeStatus(); }
  catch (reason) { error.value = reason instanceof Error ? reason.message : String(reason); }
  finally { runtimeLoading.value = false; }
}

async function createProject(input: CreateProjectInput): Promise<void> {
  busy.value = true; error.value = ""; notice.value = "";
  try {
    const result = await window.launcher.createProject(input);
    await refresh(result.project.name);
    showCreate.value = false;
    announce(`“${result.project.name}”已创建并初始化。`);
  } catch (reason) { error.value = reason instanceof Error ? reason.message : String(reason); }
  finally { busy.value = false; }
}

async function selectDirectory(): Promise<void> {
  const path = await window.launcher.selectDirectory();
  if (path) createDialog.value?.setDirectory(path);
}

onMounted(async () => {
  try { await Promise.all([refresh(), refreshRuntime(true)]); }
  catch (reason) { error.value = reason instanceof Error ? reason.message : String(reason); }
  finally { loading.value = false; }
  void window.launcher.updatePrivateTools().then(() => refreshRuntime()).catch(() => undefined);
});
</script>

<template>
  <main class="app-shell">
    <header class="app-header"><div class="brand"><AppIcon /><strong>AI Dev Launcher</strong><small>v2.0</small></div><nav><button class="button secondary compact" data-testid="environment-check" @click="showEnvironment = true">◈ 环境状态</button><button class="button secondary compact" data-testid="cli-version" @click="showVersions = true">&lt;/&gt; CLI 版本</button></nav></header>
    <div v-if="notice" class="toast success" role="status">{{ notice }}</div><div v-if="error" class="toast error" role="alert"><span>{{ error }}</span><button class="icon-button" aria-label="关闭错误" @click="error = ''">×</button></div>
    <section v-if="loading" class="center-state" data-testid="loading"><span class="spinner"></span><p>正在自动准备 AI 开发环境…</p></section>
    <section v-else-if="projects.length === 0" class="center-state empty" data-testid="empty-state"><div class="empty-icon">▱</div><h1>创建第一个项目</h1><p>只需填写名称和保存位置，其余工作将自动完成。</p><button class="button primary" @click="showCreate = true">创建新项目</button></section>
    <section v-else class="workspace"><ProjectList :projects="projects" :selected-name="selected?.name ?? null" :default-project="defaultProject" @select="selected = $event" @add="showCreate = true" /><ChatWorkspace v-if="selected" :project="selected" :runtime="runtime" /></section>
    <footer class="status-bar"><span><i class="status" :class="runtime?.status === 'ready' ? 'ready' : 'failed'"></i>{{ runtime?.status === "ready" ? "AI 环境已就绪" : "正在自动恢复" }}</span><span>Headroom {{ runtime?.headroom_version || "检测中" }}</span><span>Codex CLI {{ runtime?.codex_version || "检测中" }}</span><strong>与 Codex 桌面端独立</strong></footer>
    <AddProjectDialog v-if="showCreate" ref="createDialog" :busy="busy" @close="showCreate = false" @submit="createProject" @select-directory="selectDirectory" />
    <EnvironmentDialog v-if="showEnvironment" :runtime="runtime" :loading="runtimeLoading" @close="showEnvironment = false" @refresh="refreshRuntime(true)" />
    <CliVersionDialog v-if="showVersions" :runtime="runtime" @close="showVersions = false" />
  </main>
</template>
