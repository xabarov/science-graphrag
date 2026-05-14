import React, { useMemo, useState } from "react";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../../i18n/useI18n.js";
import { buildCommunityLegendRows } from "./graphCommunityLegend.js";
import { buildCommunityColorStyleMap, sortedCommunitiesByCount } from "../canvas/physics/communityPalette.js";
import { getScienceGraphLegendNodeChipSx, getScienceGraphNodeTypeIcon } from "../canvas/graphCanvasStyle.js";
import {
  collectGraphComposition,
  collectGraphTypeLegend,
  LEGEND_GROUPED_KINDS,
  sortLegendEdgeTypes,
  sortLegendKinds,
} from "./graphTypeLegend.js";
import { localizeEdgeTypeKey, localizeNodeKind } from "../model/graphLocalize.js";
import { CommunityClusterLegendCollapse, CommunityTypesLegendCollapse } from "./GraphTypeLegendCollapses.jsx";
import { COMMUNITY_LEGEND_TOP_N, EMPTY_COMMUNITY_MAP, NODE_KIND_GROUPS } from "./graphTypeLegendConfig.js";

/**
 * Compact legend of node and edge types in the current display graph.
 * @param {{
 *   graph: { nodes: Array<object>, edges: Array<object> },
 *   colorBy?: "type" | "community",
 *   nodeCommunityMap?: Map<string, string>,
 * }} props
 */
export default function GraphTypeLegend({ graph, colorBy = "type", nodeCommunityMap = EMPTY_COMMUNITY_MAP }) {
  const { t } = useI18n();
  const theme = useTheme();
  const tk = theme.appTokens;
  const appearance = theme.palette.mode === "light" ? "light" : "dark";
  const [chipSort, setChipSort] = useState(/** @type {"frequency" | "alphabet"} */ ("frequency"));
  const composition = useMemo(() => collectGraphComposition(graph), [graph]);
  const { nodeTypes, edgeTypes } = useMemo(() => collectGraphTypeLegend(graph), [graph]);
  const { nodeKindCounts, edgeTypeCounts, totalNodes, totalEdges } = composition;

  const presentKinds = useMemo(
    () =>
      new Set(
        (graph?.nodes || []).map((n) => {
          const kind = n?.nodeKind ?? n?.node_kind ?? n?.type;
          return kind != null && String(kind).trim() ? String(kind) : "Node";
        }),
      ),
    [graph?.nodes],
  );

  const groupedNodeKinds = useMemo(
    () =>
      NODE_KIND_GROUPS.map((entry) => ({
        groupKey: entry.groupKey,
        kinds: sortLegendKinds(
          entry.kinds.filter((kind) => presentKinds.has(kind)),
          nodeKindCounts,
          chipSort,
        ),
      })).filter((entry) => entry.kinds.length > 0),
    [presentKinds, nodeKindCounts, chipSort],
  );

  const otherKinds = useMemo(() => {
    const raw = [...presentKinds].filter((k) => !LEGEND_GROUPED_KINDS.has(k));
    return sortLegendKinds(raw, nodeKindCounts, chipSort);
  }, [presentKinds, nodeKindCounts, chipSort]);

  const sortedEdgeTypes = useMemo(
    () => sortLegendEdgeTypes([...edgeTypes], edgeTypeCounts, chipSort),
    [edgeTypes, edgeTypeCounts, chipSort],
  );

  const communityMap = nodeCommunityMap instanceof Map ? nodeCommunityMap : EMPTY_COMMUNITY_MAP;

  const communityColorStyleMap = useMemo(
    () => buildCommunityColorStyleMap(communityMap, appearance),
    [communityMap, appearance],
  );

  const totalCommunityCount = useMemo(() => sortedCommunitiesByCount(communityMap).length, [communityMap]);

  const communityRows = useMemo(() => {
    if (colorBy !== "community" || communityMap.size === 0) return [];
    return buildCommunityLegendRows(graph, communityMap, { topN: COMMUNITY_LEGEND_TOP_N, previewsPerCommunity: 3 });
  }, [colorBy, communityMap, graph]);

  const communityLegendMoreCount = useMemo(() => {
    if (colorBy !== "community") return 0;
    return Math.max(0, totalCommunityCount - COMMUNITY_LEGEND_TOP_N);
  }, [colorBy, totalCommunityCount]);

  if (nodeTypes.length === 0 && edgeTypes.length === 0) {
    return null;
  }

  const renderNodeChip = (kind, groupKey) => {
    const KindIcon = getScienceGraphNodeTypeIcon(kind);
    const dimInternal = kind === "WorkInternal";
    const count = nodeKindCounts.get(kind) ?? 0;
    const baseLabel = localizeNodeKind({ nodeKind: kind, type: kind }, t);
    return (
      <Chip
        key={`n-${groupKey}-${kind}`}
        icon={
          KindIcon ? (
            <KindIcon
              sx={{
                fontSize: "0.9rem !important",
                color: "inherit !important",
                opacity: dimInternal ? 0.65 : 0.95,
              }}
            />
          ) : undefined
        }
        label={`${baseLabel} (${count})`}
        size="small"
        sx={{
          ...getScienceGraphLegendNodeChipSx(kind, { appearance }),
          "& .MuiChip-icon": { marginLeft: "6px" },
        }}
      />
    );
  };

  const typeAndEdgeChips = (
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        gap: { xs: 0.5, sm: 0.75 },
        alignItems: "center",
      }}
    >
      {nodeTypes.length > 0 ? (
        <>
          <Typography sx={{ fontSize: "0.7rem", color: tk.text.muted, mr: 0.25 }}>
            {t("graph.legend.nodes")}
          </Typography>
          {groupedNodeKinds.map(({ groupKey, kinds }) => (
            <React.Fragment key={`grp-${groupKey}`}>
              <Typography sx={{ fontSize: "0.68rem", color: tk.text.muted, mr: 0.25 }}>
                {t(`graph.legend.group.${groupKey}`)}
              </Typography>
              {kinds.map((kind) => renderNodeChip(kind, groupKey))}
            </React.Fragment>
          ))}
          {otherKinds.length > 0 ? (
            <React.Fragment key="grp-Other">
              <Typography sx={{ fontSize: "0.68rem", color: tk.text.muted, mr: 0.25 }}>
                {t("graph.legend.group.Other")}
              </Typography>
              {otherKinds.map((kind) => renderNodeChip(kind, "Other"))}
            </React.Fragment>
          ) : null}
        </>
      ) : null}
      {sortedEdgeTypes.length > 0 ? (
        <>
          <Typography sx={{ fontSize: "0.7rem", color: tk.text.muted, ml: nodeTypes.length ? 1 : 0, mr: 0.25 }}>
            {t("graph.legend.edges")}
          </Typography>
          {sortedEdgeTypes.map((edgeType) => {
            const ec = edgeTypeCounts.get(edgeType) ?? 0;
            return (
              <Chip
                key={`e-${edgeType}`}
                icon={<ArrowForwardIcon sx={{ fontSize: "0.65rem !important", color: `${tk.text.muted} !important` }} />}
                label={`${localizeEdgeTypeKey(edgeType, t)} (${ec})`}
                size="small"
                variant="outlined"
                sx={{
                  height: 22,
                  fontSize: "0.75rem",
                  borderColor: tk.border.strong,
                  color: tk.text.secondary,
                  "& .MuiChip-icon": { marginLeft: "6px" },
                }}
              />
            );
          })}
        </>
      ) : null}
    </Box>
  );

  return (
    <Box
      sx={{
        mb: { xs: 0.75, sm: 1 },
        p: { xs: 0.5, sm: 0.75 },
        borderRadius: "6px",
        border: `1px solid ${tk.border.default}`,
        backgroundColor: tk.control.outlinedBg,
      }}
    >
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 0.75, mb: 0.65 }}>
        <Typography sx={{ fontSize: "0.68rem", color: tk.text.muted, lineHeight: 1.35 }}>
          {t("graph.legend.overviewSummary", { nodeCount: totalNodes, edgeCount: totalEdges })}
        </Typography>
        <ToggleButtonGroup
          size="small"
          value={chipSort}
          exclusive
          onChange={(_, v) => v && setChipSort(v)}
          aria-label={t("graph.legend.sortAria")}
          sx={{
            "& .MuiToggleButton-root": {
              fontSize: "0.65rem",
              py: 0.15,
              px: 0.75,
              minWidth: 0,
              textTransform: "none",
              color: tk.text.secondary,
              borderColor: tk.border.strong,
            },
            "& .MuiToggleButton-root.Mui-selected": {
              color: tk.accent.fg,
              backgroundColor: tk.accent.chipReadyBg,
            },
          }}
        >
          <ToggleButton value="frequency">{t("graph.legend.sortFrequency")}</ToggleButton>
          <ToggleButton value="alphabet">{t("graph.legend.sortAlphabet")}</ToggleButton>
        </ToggleButtonGroup>
      </Box>
      {colorBy === "community" ? (
        <Box
          sx={{
            mb: 0.55,
            pl: 0.75,
            borderLeft: `2px solid ${tk.accent.softBorder}`,
          }}
        >
          <Typography sx={{ fontSize: "0.65rem", color: tk.text.muted, lineHeight: 1.42 }}>
            {t("graph.community.legendSemanticsHint")}
          </Typography>
        </Box>
      ) : null}
      {colorBy === "community" ? (
        <CommunityTypesLegendCollapse key="community-types-legend" tk={tk} t={t}>
          {typeAndEdgeChips}
        </CommunityTypesLegendCollapse>
      ) : (
        typeAndEdgeChips
      )}
      {colorBy === "community" && totalCommunityCount > 0 ? (
        <CommunityClusterLegendCollapse
          tk={tk}
          t={t}
          totalCommunityCount={totalCommunityCount}
          communityRows={communityRows}
          communityColorStyleMap={communityColorStyleMap}
          communityLegendMoreCount={communityLegendMoreCount}
        />
      ) : null}
    </Box>
  );
}
