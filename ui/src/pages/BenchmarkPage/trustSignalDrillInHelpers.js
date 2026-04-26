/**
 * Trust / decision-gate summary helpers (BT1 drill-in + member strip).
 */

/**
 * Flatten trust_by_family payload into table rows (exported for unit tests).
 * @param {Record<string, { members?: Record<string, object> }>} trustByFamily
 * @returns {Array<{ familyKey: string, memberId: string, runtimeMode: string, isPhantom: boolean }>}
 */
export function buildTrustRows(trustByFamily) {
  const rows = [];
  if (!trustByFamily || typeof trustByFamily !== "object") return rows;
  for (const [familyKey, fam] of Object.entries(trustByFamily)) {
    const members = fam?.members && typeof fam.members === "object" ? fam.members : {};
    for (const [memberId, ts] of Object.entries(members)) {
      if (ts && typeof ts === "object") {
        rows.push({
          familyKey,
          memberId,
          runtimeMode: String(ts.runtime_mode || ""),
          isPhantom: Boolean(ts.is_phantom),
        });
      }
    }
  }
  return rows;
}

/** @param {string} decision */
export function decisionChipSx(decision) {
  const d = String(decision || "").toUpperCase();
  if (d.includes("NO-GO")) {
    return {
      backgroundColor: "rgba(239, 68, 68, 0.12)",
      border: "1px solid rgba(239, 68, 68, 0.25)",
      color: "rgba(239, 68, 68, 0.95)",
      fontWeight: 600,
      fontSize: "0.75rem",
    };
  }
  if (d.includes("CONDITIONAL")) {
    return {
      backgroundColor: "rgba(255,255,255,0.06)",
      border: "1px solid rgba(255,255,255,0.12)",
      color: "rgba(255,255,255,0.85)",
      fontWeight: 600,
      fontSize: "0.75rem",
    };
  }
  return {
    backgroundColor: "rgba(99, 102, 241, 0.15)",
    border: "1px solid rgba(99, 102, 241, 0.3)",
    color: "rgba(129, 140, 248, 0.95)",
    fontWeight: 600,
    fontSize: "0.75rem",
  };
}

/**
 * @param {Record<string, { members?: Record<string, object> }>} trustByFamily
 * @returns {string[]}
 */
export function collectConsistencyWarningLines(trustByFamily) {
  const out = [];
  if (!trustByFamily || typeof trustByFamily !== "object") return out;
  for (const [familyKey, fam] of Object.entries(trustByFamily)) {
    const members = fam?.members && typeof fam.members === "object" ? fam.members : {};
    for (const [memberId, ts] of Object.entries(members)) {
      const arr = ts?.consistency_warnings;
      if (!Array.isArray(arr)) continue;
      const ctx = `${familyKey}.${memberId}`;
      for (const raw of arr) {
        const line = String(raw ?? "").trim();
        if (!line) continue;
        const alreadyScoped =
          line.startsWith(`${memberId}:`) ||
          line.startsWith(`${ctx}:`) ||
          line.startsWith(`${ctx} `);
        out.push(alreadyScoped ? line : `${ctx}: ${line}`);
      }
    }
  }
  return out;
}

/**
 * @param {Record<string, { members?: Record<string, object> }>} trustByFamily
 * @returns {Array<{ familyKey: string, memberId: string, aggregate: string }>}
 */
export function collectValidationStatusRows(trustByFamily) {
  const out = [];
  if (!trustByFamily || typeof trustByFamily !== "object") return out;
  for (const [familyKey, fam] of Object.entries(trustByFamily)) {
    const members = fam?.members && typeof fam.members === "object" ? fam.members : {};
    for (const [memberId, ts] of Object.entries(members)) {
      if (!ts || typeof ts !== "object") continue;
      const agg = ts.validation_status_aggregate;
      if (agg == null) continue;
      const s = String(agg).trim();
      if (!s) continue;
      out.push({ familyKey, memberId, aggregate: s });
    }
  }
  return out;
}

/**
 * @param {Record<string, unknown> | null | undefined} criteria
 * @returns {Array<{ family: string, memberId: string, caseId: string, passed: boolean | null }>}
 */
export function collectAdvisoryFailureRows(criteria) {
  if (!criteria || typeof criteria !== "object") return [];
  const raw = criteria.advisory_individual_failures;
  if (!Array.isArray(raw)) return [];
  const out = [];
  for (const x of raw) {
    if (!x || typeof x !== "object") continue;
    const family = String(x.family ?? "").trim();
    const memberId = String(x.member_id ?? "").trim();
    const caseId = String(x.case_id ?? "").trim();
    const metrics = x.metrics;
    let passed = null;
    if (metrics && typeof metrics === "object" && "passed" in metrics) {
      passed = Boolean(metrics.passed);
    }
    if (!caseId && !family && !memberId) continue;
    out.push({ family, memberId, caseId, passed });
  }
  return out;
}
