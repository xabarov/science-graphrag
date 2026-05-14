/** @vitest-environment node */
import { describe, expect, it } from "vitest";

import { pickQuoteWorkTitle } from "./typedBlocks/quoteCandidatesHelpers.js";

describe("pickQuoteWorkTitle", () => {
  it("prefers title fields in order", () => {
    expect(pickQuoteWorkTitle({ title: " A " })).toBe("A");
    expect(pickQuoteWorkTitle({ work_title: "W" })).toBe("W");
    expect(pickQuoteWorkTitle({ paper_title: "P" })).toBe("P");
  });

  it("returns empty for non-objects", () => {
    expect(pickQuoteWorkTitle(null)).toBe("");
    expect(pickQuoteWorkTitle("x")).toBe("");
  });
});
