/** @vitest-environment node */
import { describe, expect, it } from "vitest";

describe("work/agent public index", () => {
  it("re-exports expected Ask integration symbols", async () => {
    const mod = await import("./index.js");
    expect(typeof mod.buildLiveStatusPresentation).toBe("function");
    expect(mod.AgentLiveStatus).toBeDefined();
    expect(typeof mod.humanizeUnknownCode).toBe("function");
  });
});
