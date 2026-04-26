import { describe, expect, it } from "vitest";

import { buildAgentHistoryDigest } from "./askSessionState.js";

describe("buildAgentHistoryDigest", () => {
  it("returns null for empty input", () => {
    expect(buildAgentHistoryDigest(null)).toBeNull();
    expect(buildAgentHistoryDigest([])).toBeNull();
  });

  it("reverses newest-first input to oldest-first digest and caps at 12 turns", () => {
    /** Same order as session thread: index 0 = newest turn. */
    const entries = Array.from({ length: 15 }, (_, i) => ({
      query: `q${14 - i}`,
      answer: `a${14 - i}`,
    }));
    const dig = buildAgentHistoryDigest(entries);
    expect(dig).toHaveLength(12);
    expect(dig[0].user).toBe("q3");
    expect(dig[0].assistant).toBe("a3");
    expect(dig[11].user).toBe("q14");
  });
});
