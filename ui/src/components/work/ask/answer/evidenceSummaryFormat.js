/**
 * Localize `evidence_summary` strings produced by `science_graphrag/agent/chat_envelope.py`
 * (e.g. "3 citation(s), 9 trace step(s)").
 *
 * @param {(key: string, vars?: Record<string, string | number>) => string} t
 * @param {unknown} raw
 * @returns {string}
 */
export function formatEvidenceSummaryForDisplay(t, raw) {
  const s = String(raw ?? "").trim();
  if (!s) return "";

  const citeTrace = /^(\d+) citation\(s\)(?:, (\d+) trace step\(s\))?$/.exec(s);
  if (citeTrace) {
    const n = citeTrace[1];
    const steps = citeTrace[2];
    if (steps) {
      return t("chat.evidenceSummary.citationsAndTrace", { citations: n, steps });
    }
    return t("chat.evidenceSummary.citationsOnly", { n });
  }

  const noCiteTrace = /^assistant reply \(no citations\)(?:, (\d+) trace step\(s\))?$/.exec(s);
  if (noCiteTrace) {
    const steps = noCiteTrace[1];
    if (steps) {
      return t("chat.evidenceSummary.noCitationsWithTrace", { steps });
    }
    return t("chat.evidenceSummary.noCitations");
  }

  return s;
}
