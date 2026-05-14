/** @vitest-environment node */
import { describe, expect, it } from "vitest";

import { deriveAnswerClass, deriveShowAsFoundPapers, deriveSourceListPresentation } from "./askSourcePresentation.js";

describe("askSourcePresentation", () => {
  it("derives inventory answer class", () => {
    expect(deriveAnswerClass({ answer_class: "inventory" })).toBe("inventory");
    expect(deriveAnswerClass({})).toBe("");
  });

  it("detects found-papers mode from inventory class", () => {
    expect(deriveShowAsFoundPapers("inventory", [{ work_id: "w1", chunk_fingerprint: "fp" }])).toBe(true);
  });

  it("detects found-papers mode when all citations are work-only", () => {
    expect(deriveShowAsFoundPapers("grounded_explanation", [{ work_id: "w1" }])).toBe(true);
  });

  it("suppresses missing-passage chrome for found-papers list", () => {
    const p = deriveSourceListPresentation("grounded_explanation", [{ work_id: "w1" }]);
    expect(p.citationListLabelKey).toBe("askPanel.citations.inventoryTitle");
    expect(p.suppressMissingPassageChrome).toBe(true);
    expect(p.allPassagesMissing).toBe(false);
  });
});
