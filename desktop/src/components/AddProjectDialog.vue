<script setup lang="ts">
import { computed, reactive, ref } from "vue";
const props = defineProps<{ busy: boolean }>();
const emit = defineEmits<{ close: []; submit: [value: { name: string; parent: string }]; selectDirectory: [] }>();
const form = reactive({ name: "", parent: "" });
const touched = ref(false);
const valid = computed(() => form.name.trim() !== "" && form.parent.trim() !== "");
const destination = computed(() => valid.value ? `${form.parent.replace(/[\\/]$/, "")}\\${form.name.trim()}` : "");
function submit(): void { touched.value = true; if (valid.value && !props.busy) emit("submit", { ...form }); }
defineExpose({ setDirectory(path: string) { form.parent = path; } });
</script>
<template>
  <div class="dialog-backdrop" @mousedown.self="$emit('close')"><section class="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
    <header><div><span class="step-label">新项目</span><h2 id="dialog-title">创建新项目</h2></div><button class="icon-button" aria-label="关闭" @click="$emit('close')">×</button></header>
    <div class="dialog-body"><label><span>项目名称</span><input v-model="form.name" data-testid="project-name" placeholder="例如 my-project" autofocus /></label><label><span>保存位置</span><div class="folder-field"><input v-model="form.parent" data-testid="project-path" placeholder="选择保存位置" readonly /><button class="button secondary compact" @click="$emit('selectDirectory')">选择位置</button></div></label><div v-if="destination" class="destination-preview"><span>将创建到</span><strong>{{ destination }}</strong></div><p v-if="touched && !valid" class="field-error">请填写项目名称并选择保存位置。</p></div>
    <footer><button class="button secondary" :disabled="busy" @click="$emit('close')">取消</button><button class="button primary" :disabled="busy" data-testid="submit-project" @click="submit">{{ busy ? "正在创建…" : "创建并进入" }}</button></footer>
  </section></div>
</template>
