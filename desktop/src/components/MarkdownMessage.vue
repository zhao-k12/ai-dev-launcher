<script setup lang="ts">
import { computed, onUnmounted, ref } from "vue";
import MarkdownIt from "markdown-it";

const props = defineProps<{ content: string }>();
const copiedIndex = ref<number | null>(null);
let copiedTimer: number | undefined;
interface Segment { type: "markdown" | "code"; content: string; language?: string; }

const markdown = new MarkdownIt({ html: false, breaks: true, linkify: true, typographer: true });
const segments = computed<Segment[]>(() => {
  const result: Segment[] = [];
  const fence = /```([^\r\n`]*)\r?\n([\s\S]*?)```/g;
  let position = 0;
  for (const match of props.content.matchAll(fence)) {
    const index = match.index ?? 0;
    if (index > position) result.push({ type: "markdown", content: props.content.slice(position, index) });
    result.push({ type: "code", language: match[1].trim() || "代码", content: match[2].replace(/\s+$/, "") });
    position = index + match[0].length;
  }
  if (position < props.content.length) result.push({ type: "markdown", content: props.content.slice(position) });
  if (!result.length) result.push({ type: "markdown", content: props.content });
  return result;
});
const render = (content: string): string => markdown.render(content);
const displayLanguage = (language?: string): string => ({ ts: "TypeScript", js: "JavaScript", py: "Python", ps1: "PowerShell" }[language?.toLowerCase() ?? ""] ?? language ?? "代码");
async function copyCode(content: string, index: number): Promise<void> {
  await window.launcher.copyText(content);
  copiedIndex.value = index;
  if (copiedTimer) window.clearTimeout(copiedTimer);
  copiedTimer = window.setTimeout(() => { copiedIndex.value = null; }, 1600);
}
onUnmounted(() => { if (copiedTimer) window.clearTimeout(copiedTimer); });
</script>

<template>
  <div class="markdown-message">
    <template v-for="(segment, index) in segments" :key="index">
      <div v-if="segment.type === 'markdown'" class="markdown-body" v-html="render(segment.content)"></div>
      <details v-else class="inline-code-details">
        <summary>
          <span>代码</span>
          <span class="code-summary-meta">
            <small>{{ displayLanguage(segment.language) }} · {{ segment.content.split('\n').length }} 行</small>
            <button class="copy-action" type="button" :title="copiedIndex === index ? '已复制' : '复制代码'" @click.stop.prevent="copyCode(segment.content, index)">
              <svg v-if="copiedIndex !== index" viewBox="0 0 20 20" aria-hidden="true"><rect x="7" y="6" width="9" height="10" rx="2"/><path d="M5 13H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v1"/></svg>
              <svg v-else viewBox="0 0 20 20" aria-hidden="true"><path d="m4 10 4 4 8-9"/></svg>
              <span class="sr-only">{{ copiedIndex === index ? "已复制" : "复制代码" }}</span>
            </button>
          </span>
        </summary>
        <pre><code>{{ segment.content }}</code></pre>
      </details>
    </template>
  </div>
</template>
