<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import AddProjectDialog from "./components/AddProjectDialog.vue";
import AppIcon from "./components/AppIcon.vue";
import ConfirmDialog from "./components/ConfirmDialog.vue";
import EnvironmentDialog from "./components/EnvironmentDialog.vue";
import InitializationWizard from "./components/InitializationWizard.vue";
import ProjectDetails from "./components/ProjectDetails.vue";
import ProjectList from "./components/ProjectList.vue";
import type {
  AddProjectInput,
  PreparationResult,
  Project,
  ToolStatus
} from "./types";

const projects = ref<Project[]>([]);
const defaultProject = ref<string | null>(null);
const selected = ref<Project | null>(null);
const loading = ref(true);
const busy = ref(false);
const error = ref("");
const notice = ref("");
const showAdd = ref(false);
const showRemove = ref(false);
const showEnvironment = ref(false);
const showInitialization = ref(false);
const preparationResult = ref<PreparationResult | null>(null);
const tools = ref<ToolStatus[]>([]);
const toolsLoading = ref(true);
const addDialog = ref<InstanceType<typeof AddProjectDialog> | null>(null);

const isDefault = computed(
  () => selected.value?.name === defaultProject.value
);
const toolMap = computed(() =>
  Object.fromEntries(tools.value.map((tool) => [tool.key, tool]))
);
const requiredToolsReady = computed(
  () =>
    toolMap.value.codex?.status === "available" &&
    toolMap.value.headroom?.status === "available"
);

async function refresh(preferred?: string): Promise<void> {
  const result = await window.launcher.listProjects();
  projects.value = result.projects;
  defaultProject.value = result.default_project;
  selected.value =
    result.projects.find((project) => project.name === preferred) ??
    result.projects.find((project) => project.name === result.default_project) ??
    result.projects[0] ??
    null;
}

async function run(action: () => Promise<void>, success: string): Promise<void> {
  busy.value = true;
  error.value = "";
  notice.value = "";
  try {
    await action();
    notice.value = success;
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason);
  } finally {
    busy.value = false;
  }
}

async function addProject(input: AddProjectInput): Promise<void> {
  await run(async () => {
    const result = await window.launcher.addProject(input);
    await refresh(result.project.name);
    showAdd.value = false;
  }, "项目添加成功。");
}

async function selectDirectory(): Promise<void> {
  const path = await window.launcher.selectDirectory();
  if (path) addDialog.value?.setDirectory(path);
}

async function makeDefault(): Promise<void> {
  if (!selected.value) return;
  await run(async () => {
    await window.launcher.setDefaultProject(selected.value!.name);
    await refresh(selected.value!.name);
  }, "默认项目已更新。");
}

async function removeProject(): Promise<void> {
  if (!selected.value) return;
  const name = selected.value.name;
  await run(async () => {
    await window.launcher.removeProject(name);
    await refresh();
    showRemove.value = false;
  }, `“${name}”已从列表移除，项目文件未删除。`);
}

async function refreshTools(): Promise<void> {
  toolsLoading.value = true;
  try {
    const result = await window.launcher.getToolStatus();
    tools.value = result.tools;
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason);
  } finally {
    toolsLoading.value = false;
  }
}

async function launchProject(): Promise<void> {
  if (!selected.value) return;
  const name = selected.value.name;
  await run(async () => {
    await window.launcher.launchProject(name);
  }, `Codex 已为“${name}”在新终端窗口启动。`);
}

function openInitialization(): void {
  notice.value = "";
  preparationResult.value = null;
  showInitialization.value = true;
}

async function prepareProject(
  dryRun: boolean,
  initializeGit: boolean
): Promise<void> {
  if (!selected.value) return;
  busy.value = true;
  error.value = "";
  try {
    preparationResult.value = await window.launcher.prepareProject(
      selected.value.name,
      dryRun,
      initializeGit
    );
    if (!dryRun) notice.value = "项目初始化完成。";
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason);
  } finally {
    busy.value = false;
  }
}

onMounted(async () => {
  try {
    await Promise.all([refresh(), refreshTools()]);
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <main class="app-shell">
    <header class="app-header">
      <div class="brand"><AppIcon /><strong>AI Dev Launcher</strong></div>
      <button class="button secondary compact" @click="showAdd = true">
        ＋ 添加项目
      </button>
    </header>

    <div v-if="notice" class="toast success" role="status">{{ notice }}</div>
    <div v-if="error" class="toast error" role="alert">
      <span>{{ error }}</span>
      <button class="icon-button" aria-label="关闭错误" @click="error = ''">×</button>
    </div>

    <section v-if="loading" class="center-state" data-testid="loading">
      <span class="spinner"></span>
      <p>正在加载项目…</p>
    </section>

    <section v-else-if="projects.length === 0" class="center-state empty" data-testid="empty-state">
      <div class="empty-icon">▱</div>
      <h1>尚未添加项目</h1>
      <p>添加现有项目，开始管理本地 AI 开发环境。</p>
      <button class="button primary" @click="showAdd = true">添加第一个项目</button>
    </section>

    <section v-else class="workspace">
      <ProjectList
        :projects="projects"
        :selected-name="selected?.name ?? null"
        :default-project="defaultProject"
        @select="selected = $event"
        @add="showAdd = true"
      />
      <ProjectDetails
        v-if="selected"
        :project="selected"
        :is-default="isDefault"
        :busy="busy"
        :can-launch="requiredToolsReady"
        @launch="launchProject"
        @initialize="openInitialization"
        @make-default="makeDefault"
        @remove="showRemove = true"
      />
    </section>

    <footer class="status-bar">
      <span>
        <i class="status" :class="toolMap.codex?.status === 'available' ? 'ready' : 'failed'"></i>
        Codex：{{ toolMap.codex?.status === "available" ? "已检测" : "未就绪" }}
      </span>
      <span>
        <i class="status" :class="toolMap.headroom?.status === 'available' ? 'ready' : 'failed'"></i>
        Headroom：{{ toolMap.headroom?.status === "available" ? "已检测" : "未就绪" }}
      </span>
      <button data-testid="environment-check" @click="showEnvironment = true">环境检查</button>
    </footer>

    <AddProjectDialog
      v-if="showAdd"
      ref="addDialog"
      :busy="busy"
      @close="showAdd = false"
      @submit="addProject"
      @select-directory="selectDirectory"
    />
    <ConfirmDialog
      v-if="showRemove && selected"
      :project-name="selected.name"
      :busy="busy"
      @cancel="showRemove = false"
      @confirm="removeProject"
    />
    <EnvironmentDialog
      v-if="showEnvironment"
      :tools="tools"
      :loading="toolsLoading"
      @close="showEnvironment = false"
      @refresh="refreshTools"
    />
    <InitializationWizard
      v-if="showInitialization && selected"
      :project="selected"
      :result="preparationResult"
      :busy="busy"
      @close="showInitialization = false"
      @preview="prepareProject(true, $event)"
      @apply="prepareProject(false, $event)"
    />
  </main>
</template>
