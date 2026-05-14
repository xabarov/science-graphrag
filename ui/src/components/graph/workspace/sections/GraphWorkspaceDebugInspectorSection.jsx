import React from "react";
import Box from "@mui/material/Box";

import GraphDebugInspector from "../../shell/GraphDebugInspector.jsx";

/**
 * @param {{
 *   visible: boolean,
 *   maxHeight: number,
 *   payload: object,
 * }} props
 */
export default function GraphWorkspaceDebugInspectorSection({ visible, maxHeight, payload }) {
  return (
    <Box sx={{ mt: 1 }}>
      <GraphDebugInspector visible={visible} maxHeight={maxHeight} payload={payload} />
    </Box>
  );
}
