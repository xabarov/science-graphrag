/**
 * @param {string} stroke
 * @returns {string}
 */
export function strokeAtHalfAlpha(stroke) {
  const m = String(stroke).match(/rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)/i);
  if (m) {
    const a = Math.min(1, (parseFloat(m[4]) || 0.5) * 0.5);
    return `rgba(${m[1]}, ${m[2]}, ${m[3]}, ${a})`;
  }
  const m2 = String(stroke).match(/rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/i);
  if (m2) return `rgba(${m2[1]}, ${m2[2]}, ${m2[3]}, 0.5)`;
  return stroke;
}
