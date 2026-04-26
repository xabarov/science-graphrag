import { describe, expect, it } from "vitest";

import { ingestProductPhaseKey, ingestStageIdFromRow, pickActiveIngestStage } from "./ingestStripModel.js";

describe("pickActiveIngestStage", () => {
  it("prefers running stage", () => {
    const stages = [
      { name: "parse_pdf", status: "completed" },
      { name: "embed", status: "running" },
    ];
    expect(pickActiveIngestStage(stages)?.name).toBe("embed");
  });

  it("falls back to last failed then last row", () => {
    const stages = [
      { name: "a", status: "completed" },
      { name: "b", status: "failed" },
    ];
    expect(pickActiveIngestStage(stages)?.name).toBe("b");
  });
});

describe("ingestProductPhaseKey", () => {
  it("maps embed to preparing_search", () => {
    expect(ingestProductPhaseKey("embed")).toBe("preparing_search");
  });

  it("defaults unknown stages to preparing_document", () => {
    expect(ingestProductPhaseKey("unknown_stage")).toBe("preparing_document");
  });
});

describe("ingestStageIdFromRow", () => {
  it("prefers stage over name", () => {
    expect(ingestStageIdFromRow({ stage: "x", name: "y" })).toBe("x");
  });
});
