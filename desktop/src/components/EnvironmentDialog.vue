<script setup lang="ts">
import type { ToolStatus } from "../types";

defineProps<{
  tools: ToolStatus[];
  loading: boolean;
}>();

defineEmits<{ close: []; refresh: [] }>();
</script>

<template>
  <div class="dialog-backdrop" @mousedown.self="$emit('close')">
    <section class="dialog environment-dialog" role="dialog" aria-modal="true">
      <header>
        <div>
          <h2>开发环境检查</h2>
          <p>检查 AI Dev Launcher 使用的本地工具。</p>
        </div>
        <button class="icon-button" aria-label="关闭环境检查" @click="$emit('close')">×</button>
      </header>
      <div class="tool-list">
        <div v-if="loading" class="tool-loading">
          <span class="spinner"></span> 正在检测环境…
        </div>
        <article v-for="tool in tools" v-else :key="tool.key" class="tool-row">
          <i
            class="tool-dot"
            :class="tool.status === 'available' ? 'ready' : tool.required ? 'failed' : 'optional'"
          ></i>
          <div class="tool-copy">
            <strong>{{ tool.display_name }}</strong>
            <span v-if="tool.status === 'available'">{{ tool.version || "已安装" }}</span>
            <span v-else>{{ tool.detail || "未找到" }}</span>
            <small v-if="tool.path">{{ tool.path }}</small>
            <small v-else-if="tool.install_hint">{{ tool.install_hint }}</small>
          </div>
          <span class="tool-label" :class="tool.status">
            {{
              tool.status === "available"
                ? "可用"
                : tool.required
                  ? "需处理"
                  : "可选"
            }}
          </span>
        </article>
      </div>
      <footer>
        <button class="button secondary" @click="$emit('close')">关闭</button>
        <button class="button primary" :disabled="loading" data-testid="refresh-tools" @click="$emit('refresh')">
          重新检测
        </button>
      </footer>
    </section>
  </div>
</template>
