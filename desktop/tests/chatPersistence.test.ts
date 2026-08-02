import { beforeEach, describe, expect, it, vi } from "vitest";
import { loadSessions, persistSessions } from "../src/chatPersistence";

describe("chat persistence", () => {
  beforeEach(() => localStorage.clear());

  it("drops transient status and image previews", () => {
    const result = persistSessions("chat", [{ messages: [
      { role: "status", text: "running" },
      { role: "user", text: "hello", uploads: [{ preview: "large-data-url" }] }
    ] }]);
    expect(result).toBe("full");
    expect(localStorage.getItem("chat")).not.toContain("large-data-url");
    expect(loadSessions<{ messages: unknown[] }>("chat")[0].messages).toHaveLength(1);
  });

  it("compacts reproducible tool output when the full write exceeds quota", () => {
    const original = Storage.prototype.setItem;
    let attempts = 0;
    const write = vi.spyOn(Storage.prototype, "setItem").mockImplementation(function (this: Storage, key, value) {
      attempts += 1;
      if (attempts === 1) throw new DOMException("quota", "QuotaExceededError");
      return original.call(this, key, value);
    });
    const result = persistSessions("chat", [{ messages: [
      { role: "user", text: "keep me" },
      { role: "tool", text: "x".repeat(20_000) }
    ] }]);
    expect(result).toBe("compacted");
    expect(localStorage.getItem("chat")).toContain("keep me");
    expect(localStorage.getItem("chat")).toContain("较早的执行输出已压缩");
    write.mockRestore();
  });
});
