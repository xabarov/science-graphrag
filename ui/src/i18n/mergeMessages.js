/** @param {Record<string, string>[]} parts */
export function mergeMessages(...parts) {
  return Object.assign({}, ...parts);
}
