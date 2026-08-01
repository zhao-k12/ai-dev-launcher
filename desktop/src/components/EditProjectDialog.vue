<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import type { Project, UpdateProjectInput } from "../types";

const props = defineProps<{ project: Project; busy: boolean }>();
const emit = defineEmits<{ close: []; submit: [value: UpdateProjectInput]; selectDirectory: [] }>();
const originalParent = props.project.path.replace(/[\\/][^\\/]+$/, "");
const folderName = props.project.path.split(/[\\/]/).filter(Boolean).at(-1) ?? props.project.name;
const form = reactive({ name: props.project.name, parent: originalParent });
const touched = ref(false);
const valid = computed(() => form.name.trim() !== "" && form.parent.trim() !== "");
const moved = computed(() => form.parent.trim().replace(/[\\/]$/, "").toLocaleLowerCase() !== originalParent.replace(/[\\/]$/, "").toLocaleLowerCase());
const destination = computed(() => moved.value ? `${form.parent.replace(/[\\/]$/, "")}\\${folderName}` : props.project.path);
function submit(): void {
  touched.value = true;
  if (valid.value && !props.busy) emit("submit", { current_name: props.project.name, name: form.name.trim(), parent: form.parent.trim() });
}
defineExpose({ setDirectory(path: string) { form.parent = path; } });
</script>

<template>
  <div class="dialog-backdrop" @mousedown.self="$emit('close')"><section class="dialog edit-project-dialog" role="dialog" aria-modal="true" aria-labelledby="edit-project-title">
    <header><div><span class="step-label">项目设置</span><h2 id="edit-project-title">编辑项目</h2></div><button class="icon-button" aria-label="关闭" @click="$emit('close')">×</button></header>
    <div class="dialog-body">
      <label><span>项目名称</span><input v-model="form.name" data-testid="edit-project-name" autofocus /></label>
      <label><span>保存位置</span><div class="folder-field"><input v-model="form.parent" data-testid="edit-project-parent" readonly /><button class="button secondary compact" type="button" @click="$emit('selectDirectory')">选择位置</button></div></label>
      <div class="destination-preview"><span>{{ moved ? "项目将移动到" : "项目当前位置" }}</span><strong>{{ destination }}</strong></div>
      <p v-if="moved" class="move-warning">保存后会把项目中的全部文件移动到新位置；成功后原位置将被删除。目标位置不能已有同名文件夹。</p>
      <p v-if="touched && !valid" class="field-error">请填写项目名称并选择保存位置。</p>
    </div>
    <footer><button class="button secondary" :disabled="busy" @click="$emit('close')">取消</button><button class="button primary" data-testid="save-project" :disabled="busy" @click="submit">{{ busy ? "正在保存…" : "保存更改" }}</button></footer>
  </section></div>
</template>
