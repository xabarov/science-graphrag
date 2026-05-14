import React, { useState } from "react";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";

import { truncateCanvasLabel } from "../canvas/graphCanvasStyle.js";
import { COMMUNITY_LEGEND_TOP_N } from "./graphTypeLegendConfig.js";

/**
 * Collapsible entity-type chips when canvas uses community fill (starts collapsed).
 * Remount with `key` when toggling color mode so the default stays collapsed.
 * @param {{ tk: object, t: (k: string, v?: object) => string, children: React.ReactNode }} props
 */
export function CommunityTypesLegendCollapse({ tk, t, children }) {
  const [open, setOpen] = useState(false);
  return (
    <Box sx={{ mb: 0.5, opacity: 0.9 }}>
      <Box
        onClick={() => setOpen((v) => !v)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setOpen((v) => !v);
          }
        }}
        role="button"
        tabIndex={0}
        aria-expanded={open}
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 0.35,
          cursor: "pointer",
          userSelect: "none",
        }}
      >
        <ExpandMoreIcon
          sx={{
            fontSize: "1.05rem",
            color: tk.text.muted,
            transform: open ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform 0.18s ease",
          }}
        />
        <Typography sx={{ fontSize: "0.68rem", color: tk.text.muted, fontWeight: 500 }}>
          {t("graph.community.typesLegendToggle")}
        </Typography>
      </Box>
      <Collapse in={open}>
        <Box sx={{ opacity: 0.92, "& .MuiChip-root": { opacity: 0.92 } }}>{children}</Box>
      </Collapse>
    </Box>
  );
}

/**
 * Collapsible "Communities" cluster list in the legend (starts collapsed).
 * Only mounted while `colorBy === "community"` so toggling away resets to collapsed.
 * @param {{
 *   tk: object,
 *   t: (k: string, v?: object) => string,
 *   totalCommunityCount: number,
 *   communityRows: Array<object>,
 *   communityColorStyleMap: Map<string, { fill?: string, stroke?: string }>,
 *   communityLegendMoreCount: number,
 * }} props
 */
export function CommunityClusterLegendCollapse({
  tk,
  t,
  totalCommunityCount,
  communityRows,
  communityColorStyleMap,
  communityLegendMoreCount,
}) {
  const [open, setOpen] = useState(false);
  return (
    <Box sx={{ mt: 0.75, pt: 0.65, borderTop: `1px solid ${tk.border.default}` }}>
      <Box
        onClick={() => setOpen((v) => !v)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setOpen((v) => !v);
          }
        }}
        role="button"
        tabIndex={0}
        aria-expanded={open}
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 0.35,
          cursor: "pointer",
          userSelect: "none",
          mb: open ? 0.5 : 0,
        }}
      >
        <ExpandMoreIcon
          sx={{
            fontSize: "1.1rem",
            color: tk.text.muted,
            transform: open ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform 0.18s ease",
          }}
        />
        <Typography sx={{ fontSize: "0.7rem", color: tk.text.muted, fontWeight: 600 }}>
          {t("graph.community.legendTitle", { count: totalCommunityCount })}
        </Typography>
      </Box>
      <Collapse in={open}>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.45 }}>
          <Typography sx={{ fontSize: "0.62rem", color: tk.text.faint, lineHeight: 1.42, mb: 0.1 }}>
            {t("graph.community.legendClusterListHint", { topN: COMMUNITY_LEGEND_TOP_N })}
          </Typography>
          {communityRows.map((row) => {
            const cs = communityColorStyleMap.get(row.communityId) || {};
            const previews = row.previews.map((p) => truncateCanvasLabel(p, 22)).join(t("graph.community.legendPreviewSep"));
            return (
              <Box
                key={`c-${row.communityId}`}
                sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.5, rowGap: 0.25 }}
              >
                <Box
                  aria-hidden
                  sx={{
                    width: 10,
                    height: 10,
                    borderRadius: "50%",
                    flexShrink: 0,
                    backgroundColor: cs.fill || "rgba(148,163,184,0.35)",
                    border: `1px solid ${cs.stroke || tk.border.strong}`,
                  }}
                />
                <Typography sx={{ fontSize: "0.68rem", color: tk.text.secondary, lineHeight: 1.35 }}>
                  {t("graph.community.legendItem.withRank", {
                    rank: row.rankOneBased,
                    count: row.count,
                    previews,
                  })}
                </Typography>
              </Box>
            );
          })}
          {communityLegendMoreCount > 0 ? (
            <Typography sx={{ fontSize: "0.65rem", color: tk.text.faint, fontStyle: "italic", mt: 0.15, lineHeight: 1.45 }}>
              {t("graph.community.legendMoreRows", { count: communityLegendMoreCount, topN: COMMUNITY_LEGEND_TOP_N })}
            </Typography>
          ) : null}
        </Box>
      </Collapse>
    </Box>
  );
}
