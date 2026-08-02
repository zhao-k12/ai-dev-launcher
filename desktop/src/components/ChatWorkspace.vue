<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import type { ChatEvent, ImageArtifact, Project, RuntimeStatus } from "../types";
import ArtifactGallery from "./ArtifactGallery.vue";
import MarkdownMessage from "./MarkdownMessage.vue";

type Permission = "standard" | "full";
interface PendingImage { path: string; name: string; preview: string; }
interface Message { id: string; role: "user" | "assistant" | "tool" | "status" | "notice"; text: string; artifacts?: ImageArtifact[]; uploads?: PendingImage[]; }
interface Session { id: string; codexSessionId?: string; name: string; messages: Message[]; updatedAt: string; turnCount?: number; lastInputTokens?: number; topicChars?: number; }
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
const AUTO_ROTATE_TOKENS = 180_000;
const AUTO_ROTATE_TURNS = 40;
const AUTO_ROTATE_CHARS = 500_000;

function save(): void {
  const persisted = sessions.value.map((session) => ({ ...session, messages: session.messages.filter((message) => message.role !== "status").map(({ uploads: _uploads, ...message }) => message) }));
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
}
function newSession(): void { const item: Session = { id: uid(), name: "新会话", messages: [], updatedAt: new Date().toISOString() }; sessions.value.unshift(item); activeId.value = item.id; save(); void scrollToLatest(); }
function appendTo(session: Session | null, role: Message["role"], text: string): void {
  if (!session) return;
  if (role === "tool") {
    let lastUser = -1;
    for (let index = session.messages.length - 1; index >= 0; index -= 1) {
      if (session.messages[index].role === "user") { lastUser = index; break; }
    }
    const group = session.messages.slice(lastUser + 1).find((message) => message.role === "tool");
    if (group) group.text = `${group.text}\n\n──────────\n\n${text}`;
    else session.messages.push({ id: uid(), role, text });
  } else session.messages.push({ id: uid(), role, text });
  session.updatedAt = new Date().toISOString(); save(); if (session.id === activeId.value) void scrollToLatest();
}
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
function numericUsage(event: Record<string, unknown>, key: string): number {
  const usage = (event.usage ?? {}) as Record<string, unknown>;
  const value = Number(usage[key] ?? 0);
  return Number.isFinite(value) && value > 0 ? value : 0;
}
function shouldRotate(session: Session): boolean {
  return Boolean(session.codexSessionId) && ((session.lastInputTokens ?? 0) >= AUTO_ROTATE_TOKENS || (session.turnCount ?? 0) >= AUTO_ROTATE_TURNS || (session.topicChars ?? 0) >= AUTO_ROTATE_CHARS);
}
function recentHandoff(session: Session): string {
  const relevant = session.messages.filter((message) => message.role === "user" || message.role === "assistant").slice(-12);
  let transcript = relevant.map((message) => `${message.role === "user" ? "用户" : "Codex"}：${message.text}`).join("\n\n");
  if (transcript.length > 18_000) transcript = transcript.slice(-18_000);
  return transcript;
}
function rotateSession(session: Session): string {
  const handoff = recentHandoff(session);
  session.codexSessionId = undefined;
  session.turnCount = 0;
  session.lastInputTokens = 0;
  session.topicChars = 0;
  session.messages.push({ id: uid(), role: "notice", text: "当前后台会话已达到较高上下文阈值，已自动续接到新会话，并携带最近对话作为任务交接。界面聊天记录仍保留。" });
  save();
  return handoff;
}
function isImplementationPlan(text: string): boolean {
  if (text.length < 240) return false;
  const markers = [/实施计划/i, /开发计划/i, /执行计划/i, /验收(?:标准|条件)/i, /Phase\s*\d/i, /阶段\s*[一二三四五六七八九\d]/i, /修改文件/i, /执行步骤/i];
  return markers.filter((pattern) => pattern.test(text)).length >= 2;
}
function executionPrompt(text: string): { prompt: string; plan: boolean } {
  const plan = isImplementationPlan(text);
  if (!plan) return { prompt: text, plan: false };
  return {
    plan: true,
    prompt: `以下内容是用户已经批准的实施计划。请快速核对它与项目实际是否存在关键冲突，然后直接实施并完成必要验证；不要重新撰写、扩展或替换计划。只有遇到无法安全解决的关键冲突时才暂停说明。\n\n${text}`
  };
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
    if (text) {
      appendTo(target, item.type === "agent_message" ? "assistant" : "tool", text);
      if (item.type === "agent_message") target.topicChars = (target.topicChars ?? 0) + text.length;
    }
    else if (item.type === "command_execution") appendTo(target, "tool", `${String(item.command ?? "命令")}\n${String(item.aggregated_output ?? "")}`.trim());
  }
  if (type === "turn.completed") {
    target.turnCount = (target.turnCount ?? 0) + 1;
    target.lastInputTokens = Math.max(target.lastInputTokens ?? 0, numericUsage(event, "input_tokens"));
    clearStatus(target);
    const finishedTask = runningTask.value;
    const startedAt = runningStartedAt.value;
    const projectName = runningProjectName.value;
    runningTask.value = null;
    runningSessionId.value = null;
    runningStartedAt.value = null;
    runningProjectName.value = null;
    if (startedAt && projectName) void attachGeneratedImages(target, projectName, startedAt);
    // Headroom may keep its wrapper alive after Codex has completed the turn.
    // Clean it up so the composer immediately returns to the send state.
    if (finishedTask) void window.launcher.stopChat(finishedTask);
  }
  save();
}
async function send(): Promise<void> {
  const text = prompt.value.trim() || (images.value.length ? "请分析这些图片。" : ""); if (!text || !active.value || runningTask.value) return;
  const handoff = shouldRotate(active.value) ? rotateSession(active.value) : "";
  const prepared = executionPrompt(text);
  const submittedPrompt = handoff
    ? `这是从同一任务的上一后台会话自动续接过来的最近上下文。请保持任务连续性，不要重新开始需求分析：\n\n${handoff}\n\n用户最新消息：\n${prepared.prompt}`
    : prepared.prompt;
  const submittedImages = [...images.value];
  const imagePaths = images.value.map((item) => item.path);
  error.value = ""; prompt.value = ""; images.value = [];
  if (active.value.name === "新会话") active.value.name = text.slice(0, 24);
  active.value.messages.push({ id: uid(), role: "user", text, uploads: submittedImages });
  active.value.topicChars = (active.value.topicChars ?? 0) + text.length;
  active.value.updatedAt = new Date().toISOString();
  save(); void scrollToLatest();
  if (prepared.plan) append("notice", "已识别为批准后的实施计划，将直接交给 Codex 执行，不再重新制定计划。");
  append("status", "Codex 正在思考和执行…");
  const taskId = uid(); runningTask.value = taskId; runningSessionId.value = active.value.id;
  runningStartedAt.value = Date.now() / 1000; runningProjectName.value = props.project.name;
  try { await window.launcher.startChat({ task_id: taskId, name: props.project.name, prompt: submittedPrompt, permission: permission.value, session_id: active.value.codexSessionId, images: imagePaths }); }
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
      <div ref="messageList" class="message-list" data-testid="message-list"><div v-if="!active?.messages.length" class="chat-empty"><div class="chat-mark">✳</div><strong>有什么可以帮你？</strong><span>直接描述任务，Codex 将在当前项目中工作。</span></div><article v-for="message in active?.messages ?? []" :key="message.id" :class="['message', message.role]"><span>{{ message.role === "user" ? "你" : message.role === "assistant" ? "Codex" : message.role === "tool" ? "执行详情" : message.role === "notice" ? "自动管理" : "状态" }}</span><details v-if="message.role === 'tool'" class="tool-details"><summary>已完成代码或工具操作（点击查看）</summary><pre>{{ message.text }}</pre></details><template v-else-if="message.role === 'assistant'"><MarkdownMessage :content="message.text" /><ArtifactGallery v-if="message.artifacts?.length" :project-name="project.name" :images="message.artifacts" /><div class="message-actions"><button type="button" :title="copiedMessageId === message.id ? '已复制' : '复制回复'" @click="copyMessage(message)"><svg v-if="copiedMessageId !== message.id" viewBox="0 0 20 20" aria-hidden="true"><rect x="7" y="6" width="9" height="10" rx="2"/><path d="M5 13H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v1"/></svg><svg v-else viewBox="0 0 20 20" aria-hidden="true"><path d="m4 10 4 4 8-9"/></svg><span>{{ copiedMessageId === message.id ? "已复制" : "复制" }}</span></button></div></template><template v-else><div v-if="message.uploads?.length" class="message-upload-images"><img v-for="image in message.uploads" :key="image.path" :src="image.preview" :alt="image.name" /></div><pre>{{ message.text }}</pre></template></article></div>
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
