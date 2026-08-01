<script setup lang="ts">
import { computed } from "vue";
import MarkdownIt from "markdown-it";

const props = defineProps<{ content: string }>();
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
</script>

<template>
  <div class="markdown-message">
    <template v-for="(segment, index) in segments" :key="index">
      <div v-if="segment.type === 'markdown'" class="markdown-body" v-html="render(segment.content)"></div>
      <details v-else class="inline-code-details">
        <summary><span>代码</span><small>{{ displayLanguage(segment.language) }} · {{ segment.content.split('\n').length }} 行</small></summary>
        <pre><code>{{ segment.content }}</code></pre>
      </details>
    </template>
  </div>
</template>
