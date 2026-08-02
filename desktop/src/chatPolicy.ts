export const AUTO_ROTATE_TOKENS = 180_000;
export const AUTO_ROTATE_TURNS = 40;
export const AUTO_ROTATE_CHARS = 500_000;

interface PolicyMessage { role: string; text: string; }
interface PolicySession {
  codexSessionId?: string;
  turnCount?: number;
  lastInputTokens?: number;
  topicChars?: number;
  messages: PolicyMessage[];
}

export function shouldRotate(session: PolicySession): boolean {
  return Boolean(session.codexSessionId) && (
    (session.lastInputTokens ?? 0) >= AUTO_ROTATE_TOKENS
    || (session.turnCount ?? 0) >= AUTO_ROTATE_TURNS
    || (session.topicChars ?? 0) >= AUTO_ROTATE_CHARS
  );
}

export function recentHandoff(session: PolicySession): string {
  const relevant = session.messages
    .filter((message) => message.role === "user" || message.role === "assistant")
    .slice(-12);
  let transcript = relevant
    .map((message) => `${message.role === "user" ? "用户" : "Codex"}：${message.text}`)
    .join("\n\n");
  if (transcript.length > 18_000) transcript = transcript.slice(-18_000);
  return transcript;
}

function isImplementationPlan(text: string): boolean {
  if (text.length < 240) return false;
  const markers = [/实施计划/i, /开发计划/i, /执行计划/i, /验收(?:标准|条件)/i, /Phase\s*\d/i, /阶段\s*[一二三四五六七八九\d]/i, /修改文件/i, /执行步骤/i];
  return markers.filter((pattern) => pattern.test(text)).length >= 2;
}

export function executionPrompt(text: string): { prompt: string; plan: boolean } {
  const plan = isImplementationPlan(text);
  if (!plan) return { prompt: text, plan: false };
  return {
    plan: true,
    prompt: `以下内容是用户已经批准的实施计划。请快速核对它与项目实际是否存在关键冲突，然后直接实施并完成必要验证；不要重新撰写、扩展或替换计划。只有遇到无法安全解决的关键冲突时才暂停说明。\n\n${text}`
  };
}
