import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

/**
 * @param {{
 *   edgeTypes: string[],
 *   title: string,
 *   formatEdgeType: (type: string) => string,
 *   borderColor: string,
 *   panelBg: string,
 *   textMuted: string,
 *   textSecondary: string,
 * }} props
 */
export default function GraphCanvasEdgeTypeLegend({
  edgeTypes,
  title,
  formatEdgeType,
  borderColor,
  panelBg,
  textMuted,
  textSecondary,
}) {
  if (!edgeTypes.length) return null;
  return (
    <Box
      sx={{
        position: "absolute",
        left: 8,
        bottom: 8,
        maxWidth: "min(240px, 42%)",
        p: 0.75,
        borderRadius: "6px",
        border: `1px solid ${borderColor}`,
        backgroundColor: panelBg,
        pointerEvents: "none",
      }}
    >
      <Typography sx={{ fontSize: "0.62rem", fontWeight: 600, color: textMuted, mb: 0.25 }}>{title}</Typography>
      {edgeTypes.map((tp) => (
        <Typography key={tp} sx={{ fontSize: "0.62rem", color: textSecondary, lineHeight: 1.35 }} noWrap>
          {formatEdgeType(tp)}
        </Typography>
      ))}
    </Box>
  );
}
