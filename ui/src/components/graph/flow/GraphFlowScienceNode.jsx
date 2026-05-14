import React, { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import { useTheme } from "@mui/material/styles";

import { getScienceGraphNodeStyle } from "../canvas/graphCanvasStyle.js";

/**
 * Custom node: type-colored chip (parity with {@link GraphCanvasMvp}).
 * @param {import("@xyflow/react").NodeProps<{ label: string, nodeType?: string }>} props
 */
export default memo(function GraphFlowScienceNode({ data, selected }) {
  const theme = useTheme();
  const appearance = theme.palette.mode === "light" ? "light" : "dark";
  const st = getScienceGraphNodeStyle(data.nodeType, { selected, appearance });
  const fg = appearance === "light" ? "rgba(15,23,42,0.9)" : "rgba(255,255,255,0.88)";
  return (
    <div
      style={{
        padding: "6px 10px",
        borderRadius: 8,
        border: `${st.lineWidth}px solid ${st.stroke}`,
        backgroundColor: st.fill,
        color: fg,
        fontSize: 11,
        fontWeight: 600,
        minWidth: 40,
        maxWidth: 160,
        textAlign: "center",
        lineHeight: 1.25,
      }}
    >
      <Handle type="target" position={Position.Top} id="in" style={{ opacity: 0.35, width: 7, height: 7 }} />
      {data.label}
      <Handle type="source" position={Position.Bottom} id="out" style={{ opacity: 0.35, width: 7, height: 7 }} />
    </div>
  );
});
