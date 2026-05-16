import { describe, expect, it } from "vitest";

import { extractPdfReadArtifactIdFromStreamEvents, isPdfReadUserMessage } from "./pdfReadUi.js";

describe("pdfReadUi", () => {
  it("detects canonical and legacy PDF read user messages", () => {
    expect(isPdfReadUserMessage("__sg_pdf_read_action__")).toBe(true);
    expect(isPdfReadUserMessage("[pdf-read-action]")).toBe(true);
    expect(isPdfReadUserMessage("hello")).toBe(false);
  });

  it("extracts last pdf_read_artifact_id from stream events", () => {
    const id = extractPdfReadArtifactIdFromStreamEvents([
      { type: "product_step", code: "pdf_read_extracting", pdf_read_artifact_id: "sg-pdf-a" },
      { type: "product_step", code: "pdf_read_extracting", pdf_read_artifact_id: "sg-pdf-b" },
    ]);
    expect(id).toBe("sg-pdf-b");
  });

  it("returns empty when no matching step", () => {
    expect(extractPdfReadArtifactIdFromStreamEvents([{ type: "product_step", code: "searching_literature" }])).toBe("");
    expect(extractPdfReadArtifactIdFromStreamEvents(null)).toBe("");
  });
});
