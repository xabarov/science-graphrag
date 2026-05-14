/** Shared string/family normalization for benchmark launcher prefs + run payload. */

export function normalizeString(value) {
  return typeof value === "string" ? value.trim() : "";
}

export function normalizeFamily(value) {
  const normalized = normalizeString(value) || "layer1";
  if (["layer1", "layer2", "graph"].includes(normalized)) return normalized;
  return "layer1";
}

export function isValidHttpUrl(value) {
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch (_error) {
    return false;
  }
}
