/** @typedef {import("./appTokensTypes.js").AppTokens} AppTokens */

/**
 * Shared secondary-card chrome for structured agent answer blocks (chat typed blocks).
 *
 * @param {AppTokens} tk
 */
function typedBlockOuterSx(tk) {
  return {
    mt: 1.5,
    p: 1.5,
    borderRadius: "6px",
    border: `1px solid ${tk.border.default}`,
    backgroundColor: tk.surface.panelAlt,
  };
}

export { typedBlockOuterSx };
export default typedBlockOuterSx;
