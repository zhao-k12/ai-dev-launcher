export function isExpectedHeadroomWebSocketFallback(
  event: Record<string, unknown>
): boolean {
  const message = typeof event.message === "string" ? event.message : "";
  const item = (event.item ?? {}) as Record<string, unknown>;
  const itemMessage = typeof item.message === "string" ? item.message : "";
  const combined = `${message}\n${itemMessage}`;
  const targetsLocalHeadroom = /ws:\/\/(?:127\.0\.0\.1|localhost):\d+\/p\//i.test(
    combined
  );
  return targetsLocalHeadroom && (
    /Reconnecting\.\.\. \d+\/\d+.*403 Forbidden/i.test(combined) ||
    /Falling back from WebSockets to HTTPS transport/i.test(combined)
  );
}
