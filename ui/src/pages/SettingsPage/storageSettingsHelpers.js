export function strEff(storage, path) {
  const [a, b, c] = path.split(".");
  try {
    const v = storage?.[a]?.fields?.[b]?.[c];
    if (v === null || v === undefined) return "";
    return String(v).trim();
  } catch {
    return "";
  }
}

export function boolEff(storage, path) {
  const [a, b, c] = path.split(".");
  try {
    return Boolean(storage?.[a]?.fields?.[b]?.[c]);
  } catch {
    return false;
  }
}
