import React from "react";
import Typography from "@mui/material/Typography";

import { localizeNodeKind } from "../../../model/graphLocalize.js";

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   t: (k: string, opts?: object) => string,
 *   selectedNode: object,
 * }} props
 */
export default function GraphDefaultNodeHeader({ tk, t, selectedNode }) {
  return (
    <>
      <Typography sx={{ fontSize: "0.7rem", color: tk.text.accent }}>{localizeNodeKind(selectedNode, t)}</Typography>
      <Typography sx={{ fontSize: "0.9375rem", fontWeight: 600, color: tk.text.primary, mt: 0.25, lineHeight: 1.35 }}>
        {selectedNode.displayLabel || selectedNode.label}
      </Typography>
      {selectedNode.subtitle ? (
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, mt: 0.35 }}>{selectedNode.subtitle}</Typography>
      ) : null}
    </>
  );
}
