/**
 * Human-readable message from a failed research API call (axios or generic Error).
 * Matches FastAPI-style `detail` when present.
 * @param {unknown} err
 * @returns {string}
 */
export function formatResearchApiError(err) {
  const raw = err?.response?.data?.detail;
  if (raw !== undefined && raw !== null) {
    return typeof raw === "string" ? raw : JSON.stringify(raw);
  }
  if (err != null && typeof err === "object" && "message" in err && typeof err.message === "string") {
    return err.message;
  }
  return String(err);
}
