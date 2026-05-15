/** Stable token for PDF-only Ask turns (must match server `PDF_READ_USER_MESSAGE_TOKEN`). */
export const PDF_READ_USER_MESSAGE_TOKEN = "__sg_pdf_read_action__";

const LEGACY_PDF_READ_QUERY_STUB = "[pdf-read-action]";

/** @param {string} [text] */
export function isPdfReadUserMessage(text) {
  const s = String(text || "").trim();
  return s === PDF_READ_USER_MESSAGE_TOKEN || s === LEGACY_PDF_READ_QUERY_STUB;
}
