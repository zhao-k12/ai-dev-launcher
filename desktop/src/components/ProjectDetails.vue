<script setup lang="ts">
import type { Project } from "../types";

defineProps<{
  project: Project;
  isDefault: boolean;
  busy: boolean;
  canLaunch: boolean;
}>();

defineEmits<{
  makeDefault: [];
  remove: [];
  launch: [];
  initialize: [];
}>();
</script>

<template>
  <section class="project-details">
    <p class="eyebrow">项目详情</p>
    <div class="project-hero">
      <div class="large-folder" aria-hidden="true">▱</div>
      <div>
        <h1>{{ project.name }}</h1>
        <p class="path">{{ project.path }}</p>
        <p class="registered"><span></span> 已注册</p>
      </div>
    </div>

    <div class="action-stack">
      <button
        class="button primary"
        :disabled="!canLaunch || busy"
        data-testid="launch-codex"
        :title="canLaunch ? '在新终端窗口启动 Codex' : '请先完成环境检查'"
        @click="$emit('launch')"
      >
        <span aria-hidden="true">▷</span> 启动 Codex
        <small>{{ busy ? "正在启动…" : canLaunch ? "新终端窗口" : "环境未就绪" }}</small>
      </button>
      <button
        class="button secondary"
        :disabled="isDefault || busy"
        data-testid="make-default"
        @click="$emit('makeDefault')"
      >
        ☆ {{ isDefault ? "当前默认项目" : "设为默认项目" }}
      </button>
      <button
        class="button secondary"
        :disabled="busy"
        data-testid="initialize-project"
        @click="$emit('initialize')"
      >
        ◇ 初始化项目 <small>预览并安全执行</small>
      </button>
      <button
        class="button danger"
        :disabled="busy"
        data-testid="remove-project"
        @click="$emit('remove')"
      >
        ♲ 从列表移除
      </button>
    </div>
  </section>
</template>
