/**
 * Primary content column inside DashboardLayout `main`: grows with the pane, capped on ultra-wide screens.
 */
export const MAIN_SHELL_MAX_WIDTH_CSS = "min(1680px, 100%)";

/** MUI `sx` fragment merged into top-level page wrappers. */
export const mainShellContentSx = {
  width: "100%",
  maxWidth: MAIN_SHELL_MAX_WIDTH_CSS,
  boxSizing: "border-box",
};
