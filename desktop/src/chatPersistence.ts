interface PersistedMessage {
  role: string;
  text: string;
  uploads?: unknown;
  [key: string]: unknown;
}

interface PersistedSession {
  messages: PersistedMessage[];
  [key: string]: unknown;
}

export type PersistenceResult = "full" | "compacted" | "failed";

function clean(sessions: PersistedSession[]): PersistedSession[] {
  return sessions.map((session) => ({
    ...session,
    messages: session.messages
      .filter((message) => message.role !== "status")
      .map((message) => {
        const persisted = { ...message };
        delete persisted.uploads;
        return persisted;
      })
  }));
}

function write(key: string, value: unknown): boolean {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

export function persistSessions(key: string, sessions: PersistedSession[]): PersistenceResult {
  const prepared = clean(sessions);
  if (write(key, prepared)) return "full";

  // Tool output is reproducible and often dominates storage. Preserve every
  // user/assistant message while compacting verbose execution details first.
  const compacted = prepared.map((session) => ({
    ...session,
    messages: session.messages.map((message) => message.role === "tool" && message.text.length > 12_000
      ? { ...message, text: `[较早的执行输出已压缩]\n${message.text.slice(-12_000)}` }
      : message)
  }));
  if (write(key, compacted)) return "compacted";

  // Last-resort recovery keeps the conversational record and drops old,
  // reproducible tool logs instead of allowing the entire save to fail.
  const conversational = prepared.map((session) => ({
    ...session,
    messages: session.messages.filter((message) => message.role !== "tool").slice(-300)
  }));
  return write(key, conversational) ? "compacted" : "failed";
}

export function loadSessions<T>(key: string): T[] {
  try {
    const value = JSON.parse(localStorage.getItem(key) || "[]");
    return Array.isArray(value) ? value as T[] : [];
  } catch {
    return [];
  }
}
