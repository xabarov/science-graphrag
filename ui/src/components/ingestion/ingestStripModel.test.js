import { describe, expect, it } from "vitest";
import {
  INGEST_PHASE_KEYS,
  fallbackHumanIngestStageLabel,
  ingestPhaseFromJob,
  ingestProductPhaseKey,
  ingestStageIdFromRow,
  ingestStageMessageKey,
  pickActiveIngestStage,
} from "./ingestStripModel.js";

describe("ingestStageIdFromRow", () => {
  it("prefers stage field", () => {
    expect(ingestStageIdFromRow({ stage: "embed", name: "ignored" })).toBe("embed");
  });

  it("falls back to name", () => {
    expect(ingestStageIdFromRow({ name: "chunk" })).toBe("chunk");
  });

  it("returns empty for invalid", () => {
    expect(ingestStageIdFromRow(null)).toBe("");
  });
});

describe("ingestPhaseFromJob", () => {
  it("prefers canonical ingest_phase from API when valid", () => {
    expect(ingestPhaseFromJob({ ingest_phase: "preparing_search" }, "parse_pdf")).toBe("preparing_search");
  });

  it("ignores invalid phase string and falls back to stage map", () => {
    expect(ingestPhaseFromJob({ ingest_phase: "not_a_phase" }, "embed")).toBe("preparing_search");
  });

  it("falls back to stage id when phase missing", () => {
    expect(ingestPhaseFromJob({}, "write_graph")).toBe("building_graph");
  });
});

describe("ingestProductPhaseKey", () => {
  it("maps known stages", () => {
    expect(ingestProductPhaseKey("parse_pdf")).toBe("preparing_document");
    expect(ingestProductPhaseKey("write_graph")).toBe("building_graph");
    expect(ingestProductPhaseKey("embed")).toBe("preparing_search");
    expect(ingestProductPhaseKey("attach_workspace")).toBe("finalizing");
  });

  it("defaults unknown to preparing_document", () => {
    expect(ingestProductPhaseKey("unknown_stage")).toBe("preparing_document");
  });
});

describe("ingestStageMessageKey", () => {
  it("returns keyed path for known pipeline stages", () => {
    expect(ingestStageMessageKey("embed")).toBe("workspace.strip.ingestStage.embed");
  });

  it("returns unknown for arbitrary ids", () => {
    expect(ingestStageMessageKey("custom_vendor_step")).toBe("workspace.strip.ingestStage.unknown");
  });
});

describe("fallbackHumanIngestStageLabel", () => {
  it("replaces underscores", () => {
    expect(fallbackHumanIngestStageLabel("parse_pdf")).toBe("parse pdf");
  });
});

describe("pickActiveIngestStage", () => {
  it("picks running row", () => {
    const stages = [
      { stage: "parse_pdf", status: "completed" },
      { stage: "embed", status: "running" },
    ];
    expect(pickActiveIngestStage(stages)).toEqual(stages[1]);
  });

  it("prefers last failed", () => {
    const stages = [
      { stage: "a", status: "completed" },
      { stage: "b", status: "failed" },
    ];
    expect(pickActiveIngestStage(stages)?.stage).toBe("b");
  });

  it("returns null for empty", () => {
    expect(pickActiveIngestStage([])).toBeNull();
  });
});

describe("INGEST_PHASE_KEYS", () => {
  it("has four product phases", () => {
    expect(INGEST_PHASE_KEYS).toHaveLength(4);
  });
});
