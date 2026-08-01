<script setup lang="ts">
import type { RuntimeStatus } from "../types";
defineProps<{ runtime: RuntimeStatus | null }>();
defineEmits<{ close: [] }>();
</script>
<template>
  <div class="dialog-backdrop" @mousedown.self="$emit('close')"><section class="dialog environment-dialog version-dialog" role="dialog" aria-modal="true"><header><div><span class="step-label">自动维护</span><h2>CLI 版本</h2><p>只管理启动器私有工具，不影响 Codex 桌面端和全局 CLI。</p></div><button class="icon-button" aria-label="关闭" @click="$emit('close')">×</button></header><div class="version-list"><article><div class="version-icon">H</div><div><strong>Headroom</strong><small>{{ runtime?.headroom_version || "正在检测版本" }}</small><p>自动更新，更新失败时自动回滚。</p></div><span class="version-badge">自动更新</span></article><article><div class="version-icon terminal">›_</div><div><strong>启动器私有 Codex CLI</strong><small>{{ runtime?.codex_version || "正在检测版本" }}</small><p>独立于 Codex 桌面端和用户全局 CLI。</p></div><span class="version-badge">自动更新</span></article></div><footer><span class="footer-note">所有组件均在无任务运行时自动维护。</span><button class="button primary" @click="$emit('close')">完成</button></footer></section></div>
</template>
