<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import type { FileTreeItem, HeadroomStats, Project, TerminalResult } from "../types";

const props = defineProps<{ project: Project; headroomPort?: number | null }>();
const tab = ref<"files" | "changes" | "terminal" | "stats">("files");
const files = ref<FileTreeItem[]>([]);
const statuses = ref<string[]>([]);
const selectedPath = ref("");
const content = ref("");
const diff = ref("");
const command = ref("");
const terminalHistory = ref<TerminalResult[]>([]);
const terminalBusy = ref(false);
const stats = ref<HeadroomStats>({ available: false, tokens_saved: 0, savings_percent: 0, requests: 0 });
const error = ref("");
const changedFiles = computed(() => statuses.value.map((line) => ({ code: line.slice(0, 2).trim() || "?", path: line.slice(3).split(" -> ").at(-1) ?? "" })));
const indent = (item: FileTreeItem) => `${item.path.split("/").length * 10}px`;

async function refresh(): Promise<void> {
  try {
    const [tree, changes, savings] = await Promise.all([
      window.launcher.getFileTree(props.project.name),
      window.launcher.getGitDiff(props.project.name),
      window.launcher.getHeadroomStats(props.project.name, props.headroomPort ?? undefined)
    ]);
    files.value = tree.items; statuses.value = changes.status; stats.value = savings; error.value = "";
  } catch (reason) { error.value = reason instanceof Error ? reason.message : String(reason); }
}
async function openFile(path: string): Promise<void> { selectedPath.value = path; try { content.value = (await window.launcher.readFile(props.project.name, path)).content; diff.value = (await window.launcher.getGitDiff(props.project.name, path)).diff; } catch (reason) { content.value = ""; error.value = reason instanceof Error ? reason.message : String(reason); } }
async function accept(path: string): Promise<void> { await window.launcher.stageFile(props.project.name, path); await refresh(); }
async function restore(path: string): Promise<void> { if (!window.confirm(`撤销“${path}”的未提交改动？此操作无法恢复。`)) return; await window.launcher.restoreFile(props.project.name, path); await refresh(); if (selectedPath.value === path) await openFile(path); }
async function runCommand(): Promise<void> { const value = command.value.trim(); if (!value || terminalBusy.value) return; terminalBusy.value = true; command.value = ""; try { terminalHistory.value.push(await window.launcher.runTerminal(props.project.name, value)); await refresh(); } catch (reason) { error.value = reason instanceof Error ? reason.message : String(reason); } finally { terminalBusy.value = false; } }
watch(() => props.project.path, refresh);
onMounted(refresh);
defineExpose({ refresh });
</script>

<template>
  <aside class="developer-panel"><nav class="panel-tabs"><button :class="{ active: tab === 'files' }" @click="tab = 'files'">文件</button><button :class="{ active: tab === 'changes' }" @click="tab = 'changes'">改动 <span>{{ statuses.length }}</span></button><button :class="{ active: tab === 'terminal' }" @click="tab = 'terminal'">终端</button><button :class="{ active: tab === 'stats' }" @click="tab = 'stats'">节省</button></nav><div v-if="error" class="panel-error">{{ error }}</div>
    <div v-if="tab === 'files'" class="file-browser"><button v-for="item in files" :key="item.path" :style="{ paddingLeft: indent(item) }" :disabled="item.kind === 'directory'" @click="openFile(item.path)"><span>{{ item.kind === "directory" ? "▸" : "·" }}</span>{{ item.name }}</button><div v-if="selectedPath" class="file-preview"><header>{{ selectedPath }}</header><pre>{{ content }}</pre></div></div>
    <div v-else-if="tab === 'changes'" class="changes-panel"><div v-if="!changedFiles.length" class="panel-empty">当前没有文件改动</div><article v-for="item in changedFiles" :key="item.path"><button @click="openFile(item.path)"><span>{{ item.code }}</span>{{ item.path }}</button><div><button class="accept" @click="accept(item.path)">接受</button><button class="restore" :disabled="item.code === '??'" :title="item.code === '??' ? '未跟踪文件不会自动删除' : ''" @click="restore(item.path)">撤销</button></div></article><pre v-if="diff" class="diff-preview">{{ diff }}</pre></div>
    <div v-else-if="tab === 'terminal'" class="terminal-panel"><div class="terminal-output"><article v-for="(entry, index) in terminalHistory" :key="index"><strong>PS&gt; {{ entry.command }}</strong><pre>{{ entry.stdout }}{{ entry.stderr }}</pre><small>退出码 {{ entry.exit_code }}</small></article><span v-if="!terminalHistory.length">PowerShell 已就绪 · 当前目录：{{ project.path }}</span></div><div class="terminal-input"><span>PS&gt;</span><input v-model="command" data-testid="terminal-command" :disabled="terminalBusy" @keydown.enter.prevent="runCommand" /><button @click="runCommand">运行</button></div></div>
    <div v-else class="stats-panel"><div v-if="stats.available"><strong>{{ stats.tokens_saved.toLocaleString() }}</strong><span>已节省 Token</span><div><b>{{ stats.savings_percent }}%</b><small>压缩节省比例</small></div><div><b>{{ stats.requests }}</b><small>代理请求</small></div></div><div v-else class="panel-empty">Headroom 统计将在代理产生请求后显示</div></div>
  </aside>
</template>
