<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import type { Project } from "../types";

defineProps<{
  projects: Project[];
  selectedName: string | null;
  defaultProject: string | null;
}>();

const emit = defineEmits<{
  select: [project: Project];
  add: [];
  setDefault: [project: Project];
  edit: [project: Project];
}>();
const menu = ref<{ project: Project; x: number; y: number } | null>(null);
function openMenu(event: MouseEvent, project: Project): void {
  menu.value = { project, x: Math.min(event.clientX, window.innerWidth - 190), y: Math.min(event.clientY, window.innerHeight - 110) };
}
function closeMenu(): void { menu.value = null; }
function choose(action: "setDefault" | "edit"): void {
  if (!menu.value) return;
  if (action === "setDefault") emit("setDefault", menu.value.project);
  else emit("edit", menu.value.project);
  closeMenu();
}
function onKeydown(event: KeyboardEvent): void { if (event.key === "Escape") closeMenu(); }
onMounted(() => { window.addEventListener("click", closeMenu); window.addEventListener("blur", closeMenu); window.addEventListener("keydown", onKeydown); });
onUnmounted(() => { window.removeEventListener("click", closeMenu); window.removeEventListener("blur", closeMenu); window.removeEventListener("keydown", onKeydown); });
</script>

<template>
  <aside class="project-sidebar">
    <div class="sidebar-heading">
      <h2>项目</h2>
      <button class="button secondary compact" data-testid="add-project" @click="$emit('add')">
        <span aria-hidden="true">＋</span> 创建新项目
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
        @contextmenu.prevent.stop="openMenu($event, project)"
      >
        <span class="folder-icon" aria-hidden="true">⌁</span>
        <span class="project-copy">
          <strong>{{ project.name }}</strong>
          <small>{{ project.path }}</small>
        </span>
        <span v-if="defaultProject === project.name" class="badge">默认</span>
      </button>
    </div>
    <div v-if="menu" class="project-context-menu" :style="{ left: `${menu.x}px`, top: `${menu.y}px` }" @click.stop>
      <button type="button" :disabled="defaultProject === menu.project.name" @click="choose('setDefault')"><span>✓</span>设为默认</button>
      <button type="button" @click="choose('edit')"><span>✎</span>编辑项目</button>
    </div>
  </aside>
</template>
