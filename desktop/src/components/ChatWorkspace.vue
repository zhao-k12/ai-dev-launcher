<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import type { ChatEvent, ImageArtifact, Project, RuntimeStatus } from "../types";
import ArtifactGallery from "./ArtifactGallery.vue";
import MarkdownMessage from "./MarkdownMessage.vue";

type Permission = "standard" | "full";
interface Message { id: string; role: "user" | "assistant" | "tool" | "status"; text: string; artifacts?: ImageArtifact[]; }
interface Session { id: string; codexSessionId?: string; name: string; messages: Message[]; updatedAt: string; }
interface PendingImage { path: string; name: string; preview: string; }
const props = defineProps<{ project: Project; runtime: RuntimeStatus | null }>();
const sessions = ref<Session[]>([]);
const activeId = ref("");
const prompt = ref("");
const images = ref<PendingImage[]>([]);
const permission = ref<Permission>("standard");
const runningTask = ref<string | null>(null);
const runningSessionId = ref<string | null>(null);
const runningStartedAt = ref<number | null>(null);
const runningProjectName = ref<string | null>(null);
const error = ref("");
const messageList = ref<HTMLElement | null>(null);
const copiedMessageId = ref<string | null>(null);
let dispose: (() => void) | undefined;
let copiedTimer: number | undefined;
const active = computed(() => sessions.value.find((item) => item.id === activeId.value) ?? null);
const storageKey = computed(() => `ai-dev-launcher:sessions:${props.project.path}`);
const uid = () => globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;

function save(): void {
  const persisted = sessions.value.map((session) => ({ ...session, messages: session.messages.filter((message) => message.role !== "status") }));
  localStorage.setItem(storageKey.value, JSON.stringify(persisted));
}
async function scrollToLatest(): Promise<void> {
  await nextTick();
  if (messageList.value) messageList.value.scrollTop = messageList.value.scrollHeight;
}
function load(): void {
  try {
    sessions.value = (JSON.parse(localStorage.getItem(storageKey.value) || "[]") as Session[])
      .map((session) => ({ ...session, messages: session.messages.filter((message) => message.role !== "status") }));
  } catch { sessions.value = []; }
  if (!sessions.value.length) newSession(); else activeId.value = sessions.value[0].id;
  void scrollToLatest();
  const current = sessions.value.find((item) => item.id === activeId.value);
  const lastAnswer = current ? [...current.messages].reverse().find((item) => item.role === "assistant") : undefined;
  if (current && lastAnswer && !lastAnswer.artifacts?.length && /图片|图像|关键帧|\b(?:png|jpe?g|webp|gif)\b/i.test(lastAnswer.text)) {
    const completedAt = Date.parse(current.updatedAt) / 1000;
    if (Number.isFinite(completedAt)) void attachGeneratedImages(current, props.project.name, completedAt - 60 * 60);
  }
}
function newSession(): void { const item: Session = { id: uid(), name: "新会话", messages: [], updatedAt: new Date().toISOString() }; sessions.value.unshift(item); activeId.value = item.id; save(); void scrollToLatest(); }
function appendTo(session: Session | null, role: Message["role"], text: string): void { if (!session) return; session.messages.push({ id: uid(), role, text }); session.updatedAt = new Date().toISOString(); save(); if (session.id === activeId.value) void scrollToLatest(); }
function append(role: Message["role"], text: string): void { appendTo(active.value, role, text); }
function clearStatus(session: Session): void { session.messages = session.messages.filter((message) => message.role !== "status"); }
function setStatus(session: Session, text: string): void {
  clearStatus(session);
  session.messages.push({ id: uid(), role: "status", text });
  if (session.id === activeId.value) void scrollToLatest();
}
function eventText(event: Record<string, unknown>): string | null {
  const item = (event.item ?? {}) as Record<string, unknown>;
  return typeof item.text === "string" ? item.text : typeof event.text === "string" ? event.text : null;
}
async function attachGeneratedImages(session: Session, projectName: string, since: number): Promise<void> {
  try {
    const result = await window.launcher.getRecentImages(projectName, Math.max(0, since - 3), 16);
    if (!result.images.length) return;
    let message = [...session.messages].reverse().find((item) => item.role === "assistant");
    if (!message) {
      message = { id: uid(), role: "assistant", text: "已生成以下图片：" };
      session.messages.push(message);
    }
    const existing = new Set((message.artifacts ?? []).map((item) => item.path));
    message.artifacts = [...(message.artifacts ?? []), ...result.images.filter((item) => !existing.has(item.path))];
    session.updatedAt = new Date().toISOString();
    save();
    if (session.id === activeId.value) void scrollToLatest();
  } catch { /* Image previews are optional and must not turn a completed task into an error. */ }
}
function handleEvent(payload: ChatEvent): void {
  if (payload.task_id !== runningTask.value) return;
  const target = sessions.value.find((item) => item.id === runningSessionId.value) ?? null;
  if (!target) return;
  if (payload.type === "error") { clearStatus(target); error.value = payload.message ?? "Codex 运行失败"; save(); return; }
  if (payload.type === "log" && payload.text) { setStatus(target, payload.text); return; }
  if (payload.type === "complete") {
    const startedAt = runningStartedAt.value;
    const projectName = runningProjectName.value;
    clearStatus(target);
    runningTask.value = null;
    runningSessionId.value = null;
    runningStartedAt.value = null;
    runningProjectName.value = null;
    if (!payload.cancelled && payload.exit_code !== 0) {
      error.value = payload.message
        ? `Codex 运行失败：${payload.message}`
        : `Codex 已退出，代码 ${payload.exit_code}`;
    }
    if (!payload.cancelled && payload.exit_code === 0 && startedAt && projectName) void attachGeneratedImages(target, projectName, startedAt);
    save();
    return;
  }
  const event = payload.event ?? {};
  const type = String(event.type ?? "");
  if (type === "thread.started" && typeof event.thread_id === "string") target.codexSessionId = event.thread_id;
  if (type === "turn.started") setStatus(target, "Codex 正在思考…");
  if (type === "error" && typeof event.message === "string") setStatus(target, event.message);
  if (type === "item.started") {
    const item = (event.item ?? {}) as Record<string, unknown>;
    if (item.type === "command_execution") setStatus(target, `正在执行：${String(item.command ?? "命令")}`);
    else if (item.type && item.type !== "agent_message") setStatus(target, `工具调用：${String(item.type)}`);
  }
  if (type === "item.completed" || type.endsWith("message.completed")) {
    const item = (event.item ?? {}) as Record<string, unknown>;
    const text = eventText(event);
    if (text) appendTo(target, item.type === "agent_message" ? "assistant" : "tool", text);
    else if (item.type === "command_execution") appendTo(target, "tool", `${String(item.command ?? "命令")}\n${String(item.aggregated_output ?? "")}`.trim());
  }
  if (type === "turn.completed") clearStatus(target);
  save();
}
async function send(): Promise<void> {
  const text = prompt.value.trim() || (images.value.length ? "请分析这些图片。" : ""); if (!text || !active.value || runningTask.value) return;
  const imagePaths = images.value.map((item) => item.path);
  error.value = ""; prompt.value = ""; images.value = [];
  if (active.value.name === "新会话") active.value.name = text.slice(0, 24);
  append("user", text); append("status", "Codex 正在思考和执行…");
  const taskId = uid(); runningTask.value = taskId; runningSessionId.value = active.value.id;
  runningStartedAt.value = Date.now() / 1000; runningProjectName.value = props.project.name;
  try { await window.launcher.startChat({ task_id: taskId, name: props.project.name, prompt: text, permission: permission.value, session_id: active.value.codexSessionId, images: imagePaths }); }
  catch (reason) { runningTask.value = null; runningSessionId.value = null; runningStartedAt.value = null; runningProjectName.value = null; error.value = reason instanceof Error ? reason.message : String(reason); }
}
function fileAsDataUrl(file: File): Promise<string> { return new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result)); reader.onerror = () => reject(reader.error); reader.readAsDataURL(file); }); }
async function paste(event: ClipboardEvent): Promise<void> {
  const files = [...(event.clipboardData?.files ?? [])].filter((file) => file.type.startsWith("image/"));
  if (!files.length) return;
  event.preventDefault(); error.value = "";
  try {
    for (const file of files) {
      if (images.value.length >= 5) throw new Error("每次最多添加 5 张图片");
      if (file.size > 10 * 1024 * 1024) throw new Error("单张图片不能超过 10 MB");
      const preview = await fileAsDataUrl(file);
      const saved = await window.launcher.saveClipboardImage({ data_url: preview, name: file.name });
      images.value.push({ path: saved.path, name: file.name || "粘贴的图片", preview });
    }
  } catch (reason) { error.value = reason instanceof Error ? reason.message : String(reason); }
}
async function stop(): Promise<void> { if (runningTask.value) await window.launcher.stopChat(runningTask.value); }
async function copyMessage(message: Message): Promise<void> {
  await window.launcher.copyText(message.text);
  copiedMessageId.value = message.id;
  if (copiedTimer) window.clearTimeout(copiedTimer);
  copiedTimer = window.setTimeout(() => { copiedMessageId.value = null; }, 1600);
}
watch(() => props.project.path, load);
onMounted(() => { load(); dispose = window.launcher.onChatEvent(handleEvent); });
onUnmounted(() => { dispose?.(); if (copiedTimer) window.clearTimeout(copiedTimer); });
</script>

<template>
  <section class="chat-workspace">
    <div class="conversation">
      <div v-if="permission === 'full'" class="risk-banner">完全访问允许 Codex 操作项目外文件且不询问审批，请确认当前任务可信。</div>
      <div ref="messageList" class="message-list" data-testid="message-list"><div v-if="!active?.messages.length" class="chat-empty"><div class="chat-mark">✳</div><strong>有什么可以帮你？</strong><span>直接描述任务，Codex 将在当前项目中工作。</span></div><article v-for="message in active?.messages ?? []" :key="message.id" :class="['message', message.role]"><span>{{ message.role === "user" ? "你" : message.role === "assistant" ? "Codex" : message.role === "tool" ? "执行详情" : "状态" }}</span><details v-if="message.role === 'tool'" class="tool-details"><summary>已完成代码或工具操作（点击查看）</summary><pre>{{ message.text }}</pre></details><template v-else-if="message.role === 'assistant'"><MarkdownMessage :content="message.text" /><ArtifactGallery v-if="message.artifacts?.length" :project-name="project.name" :images="message.artifacts" /><div class="message-actions"><button type="button" :title="copiedMessageId === message.id ? '已复制' : '复制回复'" @click="copyMessage(message)"><svg v-if="copiedMessageId !== message.id" viewBox="0 0 20 20" aria-hidden="true"><rect x="7" y="6" width="9" height="10" rx="2"/><path d="M5 13H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v1"/></svg><svg v-else viewBox="0 0 20 20" aria-hidden="true"><path d="m4 10 4 4 8-9"/></svg><span>{{ copiedMessageId === message.id ? "已复制" : "复制" }}</span></button></div></template><pre v-else>{{ message.text }}</pre></article></div>
      <div v-if="error" class="chat-error">{{ error }}</div>
      <footer class="composer-shell">
        <div class="composer-card">
          <div v-if="images.length" class="composer-images"><figure v-for="(image, index) in images" :key="image.path"><img :src="image.preview" :alt="image.name" /><button type="button" title="移除图片" @click="images.splice(index, 1)">×</button></figure></div>
          <textarea v-model="prompt" data-testid="chat-prompt" placeholder="随心输入" @paste="paste" @keydown.enter.exact.prevent="send"></textarea>
          <div class="composer-toolbar">
            <div class="composer-tools">
              <span class="composer-plus" aria-hidden="true">＋</span>
              <label class="composer-permission" :class="{ elevated: permission === 'full' }"><span aria-hidden="true">◉</span><select v-model="permission" :disabled="!!runningTask"><option value="standard">标准模式</option><option value="full">完全访问</option></select></label>
            </div>
            <div class="composer-actions">
              <span class="composer-model">Codex 默认</span>
              <button v-if="runningTask" class="composer-send stop" data-testid="stop-chat" title="停止" @click="stop"><span class="sr-only">停止</span><span aria-hidden="true">■</span></button>
              <button v-else class="composer-send" data-testid="send-chat" title="发送" :disabled="runtime?.status !== 'ready' || (!prompt.trim() && !images.length)" @click="send"><span class="sr-only">发送</span><span aria-hidden="true">↑</span></button>
            </div>
          </div>
        </div>
        <small class="composer-hint">Enter 发送 · Shift+Enter 换行</small>
      </footer>
    </div>
  </section>
</template>
