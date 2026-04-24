import { describe, expect, it } from "vitest";

import { isIngestibleFileName } from "./collectIngestFiles.js";

describe("collectIngestFiles", () => {
  it("isIngestibleFileName accepts supported extensions", () => {
    expect(isIngestibleFileName("a.pdf")).toBe(true);
    expect(isIngestibleFileName("b.MD")).toBe(true);
    expect(isIngestibleFileName("c.txt")).toBe(true);
  });

  it("isIngestibleFileName rejects others", () => {
    expect(isIngestibleFileName("x.zip")).toBe(false);
    expect(isIngestibleFileName("noext")).toBe(false);
    expect(isIngestibleFileName("")).toBe(false);
  });
});
