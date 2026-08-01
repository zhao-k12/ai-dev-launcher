<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import type { ChatEvent, Project, RuntimeStatus } from "../types";

type Permission = "standard" | "full";
interface Message { id: string; role: "user" | "assistant" | "tool" | "status"; text: string; }
interface Session { id: string; codexSessionId?: string; name: string; messages: Message[]; updatedAt: string; }
const props = defineProps<{ project: Project; runtime: RuntimeStatus | null }>();
const sessions = ref<Session[]>([]);
const activeId = ref("");
const prompt = ref("");
const permission = ref<Permission>("standard");
const runningTask = ref<string | null>(null);
const runningSessionId = ref<string | null>(null);
const error = ref("");
let dispose: (() => void) | undefined;
const active = computed(() => sessions.value.find((item) => item.id === activeId.value) ?? null);
const storageKey = computed(() => `ai-dev-launcher:sessions:${props.project.path}`);
const uid = () => globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;

function save(): void { localStorage.setItem(storageKey.value, JSON.stringify(sessions.value)); }
function load(): void {
  try { sessions.value = JSON.parse(localStorage.getItem(storageKey.value) || "[]") as Session[]; } catch { sessions.value = []; }
  if (!sessions.value.length) newSession(); else activeId.value = sessions.value[0].id;
}
function newSession(): void { const item: Session = { id: uid(), name: "新会话", messages: [], updatedAt: new Date().toISOString() }; sessions.value.unshift(item); activeId.value = item.id; save(); }
function appendTo(session: Session | null, role: Message["role"], text: string): void { if (!session) return; session.messages.push({ id: uid(), role, text }); session.updatedAt = new Date().toISOString(); save(); }
function append(role: Message["role"], text: string): void { appendTo(active.value, role, text); }
function eventText(event: Record<string, unknown>): string | null {
  const item = (event.item ?? {}) as Record<string, unknown>;
  return typeof item.text === "string" ? item.text : typeof event.text === "string" ? event.text : null;
}
function handleEvent(payload: ChatEvent): void {
  if (payload.task_id !== runningTask.value) return;
  const target = sessions.value.find((item) => item.id === runningSessionId.value) ?? null;
  if (!target) return;
  if (payload.type === "error") { error.value = payload.message ?? "Codex 运行失败"; return; }
  if (payload.type === "log" && payload.text) { appendTo(target, "status", payload.text); return; }
  if (payload.type === "complete") { runningTask.value = null; runningSessionId.value = null; if (payload.exit_code !== 0) error.value = `Codex 已退出，代码 ${payload.exit_code}`; save(); return; }
  const event = payload.event ?? {};
  const type = String(event.type ?? "");
  if (type === "thread.started" && typeof event.thread_id === "string") target.codexSessionId = event.thread_id;
  if (type === "turn.started") appendTo(target, "status", "Codex 正在思考…");
  if (type === "error" && typeof event.message === "string") appendTo(target, "status", event.message);
  if (type === "item.started") {
    const item = (event.item ?? {}) as Record<string, unknown>;
    if (item.type === "command_execution") appendTo(target, "status", `正在执行：${String(item.command ?? "命令")}`);
    else if (item.type && item.type !== "agent_message") appendTo(target, "status", `工具调用：${String(item.type)}`);
  }
  if (type === "item.completed" || type.endsWith("message.completed")) {
    const item = (event.item ?? {}) as Record<string, unknown>;
    const text = eventText(event);
    if (text) appendTo(target, item.type === "agent_message" ? "assistant" : "tool", text);
    else if (item.type === "command_execution") appendTo(target, "tool", `${String(item.command ?? "命令")}\n${String(item.aggregated_output ?? "")}`.trim());
  }
  if (type === "turn.completed") appendTo(target, "status", "任务已完成");
  save();
}
async function send(): Promise<void> {
  const text = prompt.value.trim(); if (!text || !active.value || runningTask.value) return;
  error.value = ""; prompt.value = "";
  if (active.value.name === "新会话") active.value.name = text.slice(0, 24);
  append("user", text); append("status", "Codex 正在思考和执行…");
  const taskId = uid(); runningTask.value = taskId; runningSessionId.value = active.value.id;
  try { await window.launcher.startChat({ task_id: taskId, name: props.project.name, prompt: text, permission: permission.value, session_id: active.value.codexSessionId }); }
  catch (reason) { runningTask.value = null; runningSessionId.value = null; error.value = reason instanceof Error ? reason.message : String(reason); }
}
async function stop(): Promise<void> { if (runningTask.value) await window.launcher.stopChat(runningTask.value); }
watch(() => props.project.path, load);
onMounted(() => { load(); dispose = window.launcher.onChatEvent(handleEvent); });
onUnmounted(() => dispose?.());
</script>

<template>
  <section class="chat-workspace">
    <div class="conversation"><header class="conversation-header"><div><span class="workspace-kicker">{{ project.name }}</span><h2>{{ active?.name }}</h2></div></header>
      <div v-if="permission === 'full'" class="risk-banner">完全访问允许 Codex 操作项目外文件且不询问审批，请确认当前任务可信。</div>
      <div class="message-list" data-testid="message-list"><div v-if="!active?.messages.length" class="chat-empty"><div class="chat-mark">✳</div><strong>有什么可以帮你？</strong><span>直接描述任务，Codex 将在当前项目中工作。</span></div><article v-for="message in active?.messages ?? []" :key="message.id" :class="['message', message.role]"><span>{{ message.role === "user" ? "你" : message.role === "assistant" ? "Codex" : message.role === "tool" ? "工具" : "状态" }}</span><pre>{{ message.text }}</pre></article></div>
      <div v-if="error" class="chat-error">{{ error }}</div>
      <footer class="composer-shell">
        <div class="composer-card">
          <textarea v-model="prompt" data-testid="chat-prompt" placeholder="随心输入" @keydown.enter.exact.prevent="send"></textarea>
          <div class="composer-toolbar">
            <div class="composer-tools">
              <span class="composer-plus" aria-hidden="true">＋</span>
              <label class="composer-permission" :class="{ elevated: permission === 'full' }"><span aria-hidden="true">◉</span><select v-model="permission" :disabled="!!runningTask"><option value="standard">标准模式</option><option value="full">完全访问</option></select></label>
            </div>
            <div class="composer-actions">
              <span class="composer-model">Codex 默认</span>
              <button v-if="runningTask" class="composer-send stop" data-testid="stop-chat" title="停止" @click="stop"><span class="sr-only">停止</span><span aria-hidden="true">■</span></button>
              <button v-else class="composer-send" data-testid="send-chat" title="发送" :disabled="runtime?.status !== 'ready' || !prompt.trim()" @click="send"><span class="sr-only">发送</span><span aria-hidden="true">↑</span></button>
            </div>
          </div>
        </div>
        <small class="composer-hint">Enter 发送 · Shift+Enter 换行</small>
      </footer>
    </div>
  </section>
</template>
