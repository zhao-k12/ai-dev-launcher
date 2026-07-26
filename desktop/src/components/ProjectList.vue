<script setup lang="ts">
import type { Project } from "../types";

defineProps<{
  projects: Project[];
  selectedName: string | null;
  defaultProject: string | null;
}>();

defineEmits<{
  select: [project: Project];
  add: [];
}>();
</script>

<template>
  <aside class="project-sidebar">
    <div class="sidebar-heading">
      <h2>项目</h2>
      <button class="button secondary compact" data-testid="add-project" @click="$emit('add')">
        <span aria-hidden="true">＋</span> 添加项目
      </button>
    </div>
    <div class="project-list" role="list">
      <button
        v-for="project in projects"
        :key="project.name"
        class="project-row"
        :class="{ selected: selectedName === project.name }"
        :data-testid="`project-row-${project.name}`"
        role="listitem"
        @click="$emit('select', project)"
      >
        <span class="folder-icon" aria-hidden="true">▱</span>
        <span class="project-copy">
          <strong>{{ project.name }}</strong>
          <small>{{ project.path }}</small>
        </span>
        <span v-if="defaultProject === project.name" class="badge">默认</span>
      </button>
    </div>
  </aside>
</template>
