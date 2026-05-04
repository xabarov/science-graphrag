import React, { useMemo } from "react";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../../../common/index.js";
import { localizeEdgeType, localizeDirectionHintTooltip } from "../../model/graphLocalize.js";
import { localizeDirectionHint } from "./detailFormatters.js";

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   t: (k: string, opts?: object) => string,
 *   rows: Array<{ edge: object, otherId: string, otherLabel: string, readableLine: string, directionHint: string }>,
 *   relatedEdges: Array<object>,
 *   onSelectEdge?: (edgeId: string) => void,
 * }} props
 */
export default function NodeConnectionsList({ tk, t, rows, relatedEdges, onSelectEdge }) {
  const groupedRows = useMemo(() => {
    if (!rows.length) return [];
    /** @type {Map<string, typeof rows>} */
    const m = new Map();
    for (const row of rows) {
      const key = localizeEdgeType(row.edge, t);
      const prev = m.get(key);
      if (prev) prev.push(row);
      else m.set(key, [row]);
    }
    return [...m.entries()];
  }, [rows, t]);

  if (rows.length === 0 && relatedEdges.length === 0) {
    return <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted }}>{t("graph.detailPanel.noEdges")}</Typography>;
  }
  if (rows.length > 0) {
    const renderRow = ({ edge, otherLabel, readableLine, directionHint }, hideEdgeTypeChip) => {
      const dirLabel = localizeDirectionHint(directionHint, t);
      const dirTip = localizeDirectionHintTooltip(directionHint, t);
      return (
        <Box
          key={edge.id}
          component="button"
          type="button"
          onClick={() => onSelectEdge?.(edge.id)}
          sx={{
            textAlign: "left",
            cursor: "pointer",
            p: 1,
            borderRadius: "6px",
            backgroundColor: tk.surface.sidebar,
            border: `1px solid ${tk.border.default}`,
            color: "inherit",
            font: "inherit",
            "&:hover": {
              borderColor: tk.accent.emphasisHoverBorder,
              backgroundColor: tk.accent.softBg,
            },
          }}
        >
          {dirTip ? (
            <Tooltip title={dirTip} enterDelay={400} placement="top">
              <Typography
                component="span"
                sx={{
                  display: "block",
                  fontSize: "0.68rem",
                  color: tk.text.faint,
                  cursor: "help",
                }}
              >
                {dirLabel}
              </Typography>
            </Tooltip>
          ) : (
            <Typography sx={{ fontSize: "0.68rem", color: tk.text.faint }}>{dirLabel}</Typography>
          )}
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, flexWrap: "wrap", mt: 0.25 }}>
            <ArrowForwardIcon sx={{ fontSize: "0.75rem", color: tk.text.accent }} aria-hidden />
            {!hideEdgeTypeChip ? (
              <Chip
                component="span"
                size="small"
                label={localizeEdgeType(edge, t)}
                sx={{
                  height: 22,
                  fontSize: "0.7rem",
                  border: `1px solid ${tk.accent.softBorder}`,
                  backgroundColor: tk.accent.chipReadyBg,
                  color: tk.accent.chipReadyFg,
                  "& .MuiChip-label": { px: 0.75 },
                }}
              />
            ) : null}
          </Box>
          <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, mt: 0.35, lineHeight: 1.4 }}>
            → {otherLabel}
          </Typography>
          <Typography sx={{ fontSize: "0.7rem", color: tk.text.secondary, mt: 0.35, lineHeight: 1.35 }}>
            {readableLine}
          </Typography>
        </Box>
      );
    };

    return (
      <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
        {groupedRows.map(([typeLabel, group]) => (
          <Box key={typeLabel}>
            {groupedRows.length > 1 ? (
              <Typography sx={{ fontSize: "0.68rem", fontWeight: 600, color: tk.text.secondary, mb: 0.35, letterSpacing: "0.02em" }}>
                {typeLabel}
                <Typography component="span" sx={{ fontWeight: 400, color: tk.text.faint, ml: 0.5 }}>
                  ({group.length})
                </Typography>
              </Typography>
            ) : null}
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
              {group.map((row) => renderRow(row, groupedRows.length > 1))}
            </Box>
          </Box>
        ))}
      </Box>
    );
  }
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
      {relatedEdges.map((edge) => (
        <CursorSmallButton
          key={edge.id}
          type="button"
          onClick={() => onSelectEdge?.(edge.id)}
          sx={{ justifyContent: "flex-start", textAlign: "left", height: "auto", py: 0.75, alignItems: "center", gap: 0.75 }}
        >
          <ArrowForwardIcon sx={{ fontSize: "0.75rem", color: tk.text.accent, flexShrink: 0 }} aria-hidden />
          <Chip
            component="span"
            size="small"
            label={localizeEdgeType(edge, t)}
            sx={{
              height: 22,
              fontSize: "0.7rem",
              border: `1px solid ${tk.accent.softBorder}`,
              backgroundColor: tk.accent.chipReadyBg,
              color: tk.accent.chipReadyFg,
              flexShrink: 0,
              verticalAlign: "middle",
              "& .MuiChip-label": { px: 0.75 },
            }}
          />
          <Typography component="span" sx={{ fontSize: "0.75rem", color: tk.text.secondary, textAlign: "left" }}>
            {edge.source} → {edge.target}
          </Typography>
        </CursorSmallButton>
      ))}
    </Box>
  );
}
