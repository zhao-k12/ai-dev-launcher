<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import type { ImageArtifact } from "../types";

const props = defineProps<{ projectName: string; images: ImageArtifact[] }>();
const previews = ref<Record<string, string>>({});
const selected = ref<ImageArtifact | null>(null);

async function load(): Promise<void> {
  const current: Record<string, string> = {};
  await Promise.all(props.images.map(async (image) => {
    try { current[image.path] = (await window.launcher.getImagePreview(props.projectName, image.path)).data_url; }
    catch { current[image.path] = ""; }
  }));
  previews.value = current;
}
onMounted(() => void load());
watch(() => [props.projectName, props.images] as const, () => void load(), { deep: true });
</script>

<template>
  <section class="artifact-gallery" aria-label="生成的图片">
    <header><strong>生成的图片</strong><span>{{ images.length }} 张 · 点击放大</span></header>
    <div class="artifact-grid">
      <button v-for="image in images" :key="image.path" type="button" :title="image.path" @click="selected = image">
        <img v-if="previews[image.path]" :src="previews[image.path]" :alt="image.name" loading="lazy" />
        <span v-else class="artifact-loading">图片不可用</span>
        <small>{{ image.name }}</small>
      </button>
    </div>
    <div v-if="selected" class="image-lightbox" role="dialog" aria-modal="true" @click.self="selected = null">
      <button class="lightbox-close" type="button" aria-label="关闭图片预览" @click="selected = null">×</button>
      <figure><img v-if="previews[selected.path]" :src="previews[selected.path]" :alt="selected.name" /><figcaption><strong>{{ selected.name }}</strong><span>{{ selected.path }}</span></figcaption></figure>
    </div>
  </section>
</template>
