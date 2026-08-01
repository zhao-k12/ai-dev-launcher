import { describe, expect, it } from "vitest";
import { isExpectedHeadroomWebSocketFallback } from "../electron/main/chatFilters";

describe("Headroom chat event filtering", () => {
  it("hides local websocket retries and HTTPS fallback", () => {
    expect(isExpectedHeadroomWebSocketFallback({
      type: "error",
      message: "Reconnecting... 2/5 (unexpected status 403 Forbidden: Unknown error, url: ws://127.0.0.1:8787/p/app/v1/responses)"
    })).toBe(true);
    expect(isExpectedHeadroomWebSocketFallback({
      type: "item.completed",
      item: {
        type: "error",
        message: "Falling back from WebSockets to HTTPS transport. unexpected status 403 Forbidden, url: ws://localhost:8787/p/app/v1/responses"
      }
    })).toBe(true);
  });

  it("keeps genuine remote and HTTP failures", () => {
    expect(isExpectedHeadroomWebSocketFallback({
      type: "error",
      message: "401 Unauthorized: login required"
    })).toBe(false);
    expect(isExpectedHeadroomWebSocketFallback({
      type: "error",
      message: "403 Forbidden, url: https://api.openai.com/v1/responses"
    })).toBe(false);
  });
});
