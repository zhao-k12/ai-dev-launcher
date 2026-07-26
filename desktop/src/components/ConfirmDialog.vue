<script setup lang="ts">
defineProps<{ projectName: string; busy: boolean }>();
defineEmits<{ cancel: []; confirm: [] }>();
</script>

<template>
  <div class="dialog-backdrop">
    <section class="dialog confirm-dialog" role="alertdialog" aria-modal="true">
      <header><h2>移除项目</h2></header>
      <div class="dialog-body">
        <p>确定要从 AI Dev Launcher 中移除“{{ projectName }}”吗？</p>
        <p class="muted">项目文件不会被删除。</p>
      </div>
      <footer>
        <button class="button secondary" :disabled="busy" @click="$emit('cancel')">取消</button>
        <button class="button danger solid" :disabled="busy" data-testid="confirm-remove" @click="$emit('confirm')">
          {{ busy ? "正在移除…" : "确认移除" }}
        </button>
      </footer>
    </section>
  </div>
</template>
