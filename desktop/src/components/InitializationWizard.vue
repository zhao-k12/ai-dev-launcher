<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { PreparationResult, Project } from "../types";

const props = defineProps<{
  project: Project;
  result: PreparationResult | null;
  busy: boolean;
}>();

const emit = defineEmits<{
  close: [];
  preview: [initializeGit: boolean];
  apply: [initializeGit: boolean];
}>();

const initializeGit = ref(true);
const step = computed(() => {
  if (!props.result) return "options";
  return props.result.dry_run ? "preview" : "complete";
});

watch(initializeGit, () => {
  if (props.result) emit("preview", initializeGit.value);
});

function actionTitle(kind: string): string {
  return (
    {
      agents: "AGENTS.md",
      backup: "安全备份",
      git: "Git 仓库",
      metadata: "Launcher 元数据"
    }[kind] ?? kind
  );
}

function actionDetail(kind: string): string {
  return (
    {
      agents: "生成或安全更新 Launcher 管理的 AGENTS.md 区块",
      backup: "修改前备份现有 AGENTS.md",
      git: "需要时初始化本地 Git 仓库",
      metadata: "写入 AI Dev Launcher 项目元数据"
    }[kind] ?? "执行项目准备操作"
  );
}

function statusText(status: string): string {
  return (
    {
      planned: "计划",
      written: "已写入",
      created: "已备份",
      initialized: "已初始化",
      unchanged: "无需修改",
      skipped: "已跳过"
    }[status] ?? status
  );
}
</script>

<template>
  <div class="dialog-backdrop">
    <section class="dialog wizard-dialog" role="dialog" aria-modal="true">
      <header>
        <div>
          <p class="step-label">
            {{ step === "options" ? "步骤 1 / 3" : step === "preview" ? "步骤 2 / 3" : "步骤 3 / 3" }}
          </p>
          <h2>初始化项目</h2>
          <p>{{ project.name }} · {{ project.path }}</p>
        </div>
        <button class="icon-button" aria-label="关闭初始化向导" @click="$emit('close')">×</button>
      </header>

      <div v-if="step === 'options'" class="wizard-content">
        <h3>选择初始化内容</h3>
        <p class="muted">预览不会修改任何文件。执行前你会看到完整变更清单。</p>
        <label class="setup-option fixed">
          <input type="checkbox" checked disabled />
          <span>
            <strong>生成或更新 AGENTS.md</strong>
            <small>只管理 Launcher 标记区块，保留已有内容。</small>
          </span>
        </label>
        <label class="setup-option fixed">
          <input type="checkbox" checked disabled />
          <span>
            <strong>写入项目元数据</strong>
            <small>保存到 .ai-dev-launcher/project.json。</small>
          </span>
        </label>
        <label class="setup-option">
          <input v-model="initializeGit" type="checkbox" data-testid="initialize-git" />
          <span>
            <strong>需要时初始化 Git 仓库</strong>
            <small>已有 Git 仓库时不会重复执行。</small>
          </span>
        </label>
      </div>

      <div v-else-if="step === 'preview'" class="wizard-content">
        <div class="preview-heading">
          <div>
            <h3>变更预览</h3>
            <p class="muted">以下操作尚未执行。</p>
          </div>
          <span class="safe-badge">Dry run · 无写入</span>
        </div>
        <div class="action-preview">
          <article v-for="action in result?.actions" :key="`${action.kind}-${action.target}`">
            <i>✓</i>
            <div>
              <strong>{{ actionTitle(action.kind) }}</strong>
              <span>{{ actionDetail(action.kind) }}</span>
              <small>{{ action.target }}</small>
            </div>
            <em>{{ statusText(action.status) }}</em>
          </article>
        </div>
      </div>

      <div v-else class="wizard-content complete-state" data-testid="prepare-complete">
        <div class="complete-icon">✓</div>
        <h3>项目初始化完成</h3>
        <p>AGENTS.md、Launcher 元数据和所选 Git 设置均已处理。</p>
        <div class="completion-summary">
          <span v-for="action in result?.actions" :key="action.kind">
            {{ actionTitle(action.kind) }} · {{ statusText(action.status) }}
          </span>
        </div>
      </div>

      <footer>
        <button v-if="step !== 'complete'" class="button secondary" :disabled="busy" @click="$emit('close')">
          取消
        </button>
        <button
          v-if="step === 'options'"
          class="button primary"
          :disabled="busy"
          data-testid="preview-prepare"
          @click="$emit('preview', initializeGit)"
        >
          {{ busy ? "正在分析…" : "预览变更" }}
        </button>
        <button
          v-else-if="step === 'preview'"
          class="button primary"
          :disabled="busy"
          data-testid="apply-prepare"
          @click="$emit('apply', initializeGit)"
        >
          {{ busy ? "正在初始化…" : "执行初始化" }}
        </button>
        <button v-else class="button primary" data-testid="finish-prepare" @click="$emit('close')">
          完成
        </button>
      </footer>
    </section>
  </div>
</template>
