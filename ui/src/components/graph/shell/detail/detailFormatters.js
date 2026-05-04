/**
 * Pure formatters and key sets for graph inspector detail panel.
 */

/** Claim fields rendered in dedicated blocks; rest stays in the key table with i18n labels. */
export const CLAIM_DETAIL_KEYS_IN_TABLE = new Set(["normalized_text", "text", "claim_metadata"]);

/** Method rich fields rendered above the key table (ADR 023). */
export const METHOD_DETAIL_KEYS_IN_TABLE = new Set([
  "aliases",
  "description_short",
  "description_markdown",
  "description_plaintext",
  "method_kind",
  "description_source",
  "description_confidence",
]);

/**
 * @param {unknown} v
 */
export function formatPropertyValue(v) {
  if (v == null) return "—";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

/** @param {{ type?: string } | null | undefined} node */
export function isClaimSelectedNode(node) {
  return Boolean(node && String(node.type) === "Claim");
}

/** @param {Record<string, unknown>} props */
export function claimBodyFromProperties(props) {
  const norm = props?.normalized_text;
  const raw = props?.text;
  const n = typeof norm === "string" ? norm.trim() : norm != null ? String(norm).trim() : "";
  if (n) return n;
  const t = typeof raw === "string" ? raw.trim() : raw != null ? String(raw).trim() : "";
  return t || "";
}

/** @param {unknown} meta */
export function formatClaimMetadataBlock(meta) {
  if (meta == null || meta === "") return "";
  if (typeof meta === "string") {
    const s = meta.trim();
    if (!s) return "";
    try {
      return JSON.stringify(JSON.parse(s), null, 2);
    } catch {
      return s;
    }
  }
  if (typeof meta === "object") return JSON.stringify(meta, null, 2);
  return String(meta);
}

/**
 * @param {string} hint
 * @param {(k: string) => string} t
 */
export function localizeDirectionHint(hint, t) {
  const h = String(hint || "").trim().toLowerCase();
  if (!h) return "";
  const key = `graph.detailPanel.direction.${h}`;
  const out = t(key);
  return out !== key ? out : hint;
}
