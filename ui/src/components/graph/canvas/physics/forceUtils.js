/**
 * Fast math + repulsion tuning for science-graph nodes (no OSINT personId semantics).
 */

export function fastInvSqrt(x) {
  if (x === 0) return Infinity;
  if (x < 0) return NaN;
  const i = new Float32Array(1);
  i[0] = x;
  const intView = new Int32Array(i.buffer);
  intView[0] = 0x5f3759df - (intView[0] >> 1);
  let y = new Float32Array(intView.buffer)[0];
  y = y * (1.5 - 0.5 * x * y * y);
  return y;
}

export function fastSqrt(x) {
  if (x === 0) return 0;
  if (x < 0) return NaN;
  return x * fastInvSqrt(x);
}

/**
 * @param {unknown} nodeType
 * @param {unknown} otherType
 * @returns {number}
 */
export function getRepulsionMultiplier(nodeType, otherType) {
  const a = String(nodeType ?? "Node").trim();
  const b = String(otherType ?? "Node").trim();
  if (a === b) return 0.9;
  return 1.0;
}
