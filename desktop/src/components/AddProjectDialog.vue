<script setup lang="ts">
import { computed, reactive, ref } from "vue";

const props = defineProps<{ busy: boolean }>();
const emit = defineEmits<{
  close: [];
  submit: [value: { name: string; path: string; make_default: boolean }];
  selectDirectory: [];
}>();

const form = reactive({ name: "", path: "", make_default: false });
const touched = ref(false);
const valid = computed(() => form.name.trim() !== "" && form.path.trim() !== "");

function submit(): void {
  touched.value = true;
  if (valid.value && !props.busy) emit("submit", { ...form });
}

defineExpose({
  setDirectory(path: string) {
    form.path = path;
    if (!form.name) {
      form.name = path.split(/[\\/]/).filter(Boolean).at(-1) ?? "";
    }
  }
});
</script>

<template>
  <div class="dialog-backdrop" @mousedown.self="$emit('close')">
    <section class="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
      <header>
        <h2 id="dialog-title">添加项目</h2>
        <button class="icon-button" aria-label="关闭" @click="$emit('close')">×</button>
      </header>
      <div class="dialog-body">
        <label>
          <span>项目名称</span>
          <input v-model="form.name" data-testid="project-name" placeholder="输入项目名称" autofocus />
        </label>
        <label>
          <span>项目目录</span>
          <div class="folder-field">
            <input v-model="form.path" data-testid="project-path" placeholder="选择项目目录" />
            <button class="button secondary compact" @click="$emit('selectDirectory')">
              选择目录
            </button>
          </div>
        </label>
        <label class="checkbox-row">
          <input v-model="form.make_default" type="checkbox" />
          <span>添加后设为默认项目</span>
        </label>
        <p v-if="touched && !valid" class="field-error">请填写项目名称并选择项目目录。</p>
      </div>
      <footer>
        <button class="button secondary" :disabled="busy" @click="$emit('close')">取消</button>
        <button class="button primary" :disabled="busy" data-testid="submit-project" @click="submit">
          {{ busy ? "正在添加…" : "添加项目" }}
        </button>
      </footer>
    </section>
  </div>
</template>
