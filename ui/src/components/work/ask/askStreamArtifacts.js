/**
 * Helpers for product SSE artifacts (structured user question, research plan hints).
 *
 * @param {unknown[]} streamEvents
 * @returns {{ request_id: string, questions: unknown[] } | null}
 */
export function extractOpenStructuredQuestion(streamEvents) {
  const arr = Array.isArray(streamEvents) ? streamEvents : [];
  /** @type {{ request_id: string, questions: unknown[] } | null} */
  let open = null;
  for (const raw of arr) {
    if (!raw || typeof raw !== "object") continue;
    const e = /** @type {Record<string, unknown>} */ (raw);
    const typ = String(e.type || "");
    if (typ === "streamable_tool_hint") {
      const hint = e.hint && typeof e.hint === "object" ? /** @type {Record<string, unknown>} */ (e.hint) : null;
      if (hint && String(hint.type || "") === "user_question_asked" && Array.isArray(hint.questions) && hint.questions.length) {
        open = { request_id: String(hint.request_id || "").trim(), questions: hint.questions };
      }
      continue;
    }
    if (typ === "user_question_asked" && Array.isArray(e.questions) && e.questions.length) {
      open = { request_id: String(e.request_id || "").trim(), questions: e.questions };
    }
    if (typ === "user_answered" && open && String(e.request_id || "") === open.request_id) {
      open = null;
    }
  }
  if (!open || !open.request_id) return null;
  return open;
}

/**
 * @param {unknown[]} streamEvents
 * @returns {{ item_count?: number, updated_at?: number } | null}
 */
export function extractResearchPlanStreamHint(streamEvents) {
  const arr = Array.isArray(streamEvents) ? streamEvents : [];
  /** @type {{ item_count?: number, updated_at?: number } | null} */
  let last = null;
  for (const raw of arr) {
    if (!raw || typeof raw !== "object") continue;
    const e = /** @type {Record<string, unknown>} */ (raw);
    if (String(e.type || "") !== "research_plan_updated") continue;
    last = {};
    if (e.item_count != null && Number.isFinite(Number(e.item_count))) last.item_count = Number(e.item_count);
    if (e.updated_at != null && Number.isFinite(Number(e.updated_at))) last.updated_at = Number(e.updated_at);
  }
  return last;
}
