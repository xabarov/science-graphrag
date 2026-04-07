/**
 * Client-side helpers: graph CLI JSON vs gold `graph_expectations`.
 * CLI output shape: see eval/results/*graph*.json (`metrics.snapshot`, optional embedded `gold.graph_expectations`).
 */

export function extractGraphSnapshotMetrics(parsed) {
  if (!parsed || typeof parsed !== "object") return null;
  const snap = parsed.metrics?.snapshot;
  if (snap && typeof snap === "object") return snap;
  return null;
}

function _num(v) {
  if (v == null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

/**
 * @param {Record<string, unknown>} expectations - gold.graph_expectations
 * @param {Record<string, unknown>} snapshot - metrics.snapshot from CLI JSON
 * @returns {{ rows: Array<{field: string, snapshot: string, expected: string, ok: boolean}>, arxivNotes: string[] }}
 */
export function compareGraphExpectationsToSnapshot(expectations, snapshot) {
  const rows = [];
  const arxivNotes = [];

  if (!expectations || typeof expectations !== "object") {
    return { rows, arxivNotes: ["No graph_expectations in gold."] };
  }
  if (!snapshot || typeof snapshot !== "object") {
    return { rows, arxivNotes: ["No metrics.snapshot in uploaded file (expected graph benchmark JSON)."] };
  }

  const exp = expectations;
  const snap = snapshot;

  const addRange = (label, snapVal, minKey, maxKey) => {
    const v = _num(snapVal);
    if (v == null) return;
    const minc = _num(exp[minKey]);
    const maxc = _num(exp[maxKey]);
    if (minc == null && maxc == null) return;
    const ok = (minc == null || v >= minc) && (maxc == null || v <= maxc);
    rows.push({
      field: label,
      snapshot: String(v),
      expected: `${minc ?? "—"} … ${maxc ?? "—"}`,
      ok,
    });
  };

  addRange("cites_count", snap.cites_count, "min_cites", "max_cites");
  addRange("authorship_count", snap.authorship_count, "min_authorships", "max_authorships");
  addRange("institution_count", snap.institution_count, "min_institutions", "max_institutions");

  const dups = _num(snap.duplicate_work_fingerprints);
  const maxD = _num(exp.max_duplicate_work_fingerprints);
  if (dups != null && maxD != null) {
    const ok = dups <= maxD;
    rows.push({
      field: "duplicate_work_fingerprints",
      snapshot: String(dups),
      expected: `≤ ${maxD}`,
      ok,
    });
  }

  const maxViol = _num(exp.max_work_dedup_violations);
  const viol = _num(snap.work_dedup_violations ?? snap.work_dedup_violation_count);
  if (viol != null && maxViol != null) {
    rows.push({
      field: "work_dedup_violations",
      snapshot: String(viol),
      expected: `≤ ${maxViol}`,
      ok: viol <= maxViol,
    });
  }

  const expectedArxiv = Array.isArray(exp.expected_cited_arxiv_ids)
    ? exp.expected_cited_arxiv_ids.map(String)
    : [];
  const actualArxiv = Array.isArray(snap.cited_arxiv_ids) ? snap.cited_arxiv_ids.map(String) : [];

  if (expectedArxiv.length || actualArxiv.length) {
    const expSet = new Set(expectedArxiv);
    const actSet = new Set(actualArxiv);
    const missing = expectedArxiv.filter((id) => !actSet.has(id));
    const extra = actualArxiv.filter((id) => !expSet.has(id));
    arxivNotes.push(`Expected arxiv ids: ${expectedArxiv.length}, snapshot cites: ${actualArxiv.length}`);
    if (missing.length) arxivNotes.push(`Missing in snapshot (${missing.length}): ${missing.slice(0, 12).join(", ")}${missing.length > 12 ? "…" : ""}`);
    if (extra.length) arxivNotes.push(`Extra in snapshot (${extra.length}): ${extra.slice(0, 12).join(", ")}${extra.length > 12 ? "…" : ""}`);
    if (!missing.length && !extra.length && expectedArxiv.length) {
      arxivNotes.push("cited_arxiv_ids set matches expected_cited_arxiv_ids.");
    }
  }

  return { rows, arxivNotes };
}

export function graphExpectationRangeRows(ge) {
  if (!ge || typeof ge !== "object") return [];
  const keys = [
    ["min_cites", "max_cites"],
    ["min_authorships", "max_authorships"],
    ["min_institutions", "max_institutions"],
  ];
  return keys.map(([lo, hi]) => ({
    label: `${lo} / ${hi}`,
    low: ge[lo] ?? "—",
    high: ge[hi] ?? "—",
  }));
}
