<script setup lang="ts">
import type { RuntimeStatus } from "../types";
defineProps<{ runtime: RuntimeStatus | null; loading: boolean }>();
defineEmits<{ close: []; refresh: [] }>();
</script>
<template>
  <div class="dialog-backdrop" @mousedown.self="$emit('close')"><section class="dialog environment-dialog" role="dialog" aria-modal="true"><header><div><span class="step-label">只读状态</span><h2>环境状态</h2><p>所有恢复和隔离操作均由启动器自动完成。</p></div><button class="icon-button" aria-label="关闭" @click="$emit('close')">×</button></header><div v-if="loading" class="tool-loading"><span class="spinner"></span>正在自动检查…</div><div v-else class="status-page"><div class="overall-status" :class="runtime?.status"><strong>{{ runtime?.status === "ready" ? "AI 开发环境运行正常" : "正在自动恢复环境" }}</strong><span>进程级隔离 · 不修改 Codex 桌面端</span></div><article v-for="check in runtime?.checks ?? []" :key="check.key" class="status-row"><i :class="check.status">{{ check.status === "ready" ? "✓" : "!" }}</i><div><strong>{{ check.label }}</strong><small>{{ check.detail || (check.status === "ready" ? "已验证" : "等待自动恢复") }}</small></div><span>{{ check.status === "ready" ? "已就绪" : "处理中" }}</span></article></div><footer><button v-if="runtime?.status !== 'ready'" class="button secondary" @click="$emit('refresh')">重试自动恢复</button><button class="button primary" @click="$emit('close')">完成</button></footer></section></div>
</template>
