/** Stable token for PDF-only Ask turns (must match server `PDF_READ_USER_MESSAGE_TOKEN`). */
export const PDF_READ_USER_MESSAGE_TOKEN = "__sg_pdf_read_action__";

const LEGACY_PDF_READ_QUERY_STUB = "[pdf-read-action]";

/** @param {string} [text] */
export function isPdfReadUserMessage(text) {
  const s = String(text || "").trim();
  return s === PDF_READ_USER_MESSAGE_TOKEN || s === LEGACY_PDF_READ_QUERY_STUB;
}

/**
 * Best-effort stable id from SSE stream when `final_answer` (and `run_metadata`) is missing.
 *
 * @param {unknown[]} [events]
 * @returns {string}
 */
export function extractPdfReadArtifactIdFromStreamEvents(events) {
  if (!Array.isArray(events) || events.length === 0) return "";
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const ev = events[i];
    if (!ev || typeof ev !== "object") continue;
    if (ev.type !== "product_step" || ev.code !== "pdf_read_extracting") continue;
    if (ev.pdf_read_artifact_id == null) continue;
    const id = String(ev.pdf_read_artifact_id).trim();
    if (id) return id;
  }
  return "";
}
