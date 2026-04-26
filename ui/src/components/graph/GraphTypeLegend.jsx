import React, { useMemo, useState } from "react";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";

import { useI18n } from "../../i18n/I18nContext.jsx";
import { getScienceGraphLegendNodeChipSx, getScienceGraphNodeTypeIcon } from "./graphCanvasStyle.js";
import {
  collectGraphComposition,
  collectGraphTypeLegend,
  LEGEND_GROUPED_KINDS,
  sortLegendEdgeTypes,
  sortLegendKinds,
} from "./graphTypeLegend.js";
import { localizeEdgeTypeKey, localizeNodeKind } from "./graphLocalize.js";

const NODE_KIND_GROUPS = [
  {
    groupKey: "Works",
    kinds: ["Work", "WorkInternal", "WorkExternal"],
  },
  {
    groupKey: "Semantic",
    kinds: ["Method", "Dataset"],
  },
  {
    groupKey: "People",
    kinds: ["Author", "AuthorshipReification", "Authorship"],
  },
  {
    groupKey: "Context",
    kinds: ["Venue", "Institution"],
  },
];

/**
 * Compact legend of node and edge types in the current display graph.
 * @param {{ graph: { nodes: Array<object>, edges: Array<object> } }} props
 */
export default function GraphTypeLegend({ graph }) {
  const { t } = useI18n();
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
          ...getScienceGraphLegendNodeChipSx(kind),
          "& .MuiChip-icon": { marginLeft: "6px" },
        }}
      />
    );
  };

  return (
    <Box
      sx={{
        mb: { xs: 0.75, sm: 1 },
        p: { xs: 0.5, sm: 0.75 },
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "rgba(255,255,255,0.02)",
      }}
    >
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 0.75, mb: 0.65 }}>
        <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.42)", lineHeight: 1.35 }}>
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
              color: "rgba(255,255,255,0.5)",
              borderColor: "rgba(255,255,255,0.12)",
            },
            "& .MuiToggleButton-root.Mui-selected": {
              color: "rgba(129, 140, 248, 0.95)",
              backgroundColor: "rgba(99, 102, 241, 0.12)",
            },
          }}
        >
          <ToggleButton value="frequency">{t("graph.legend.sortFrequency")}</ToggleButton>
          <ToggleButton value="alphabet">{t("graph.legend.sortAlphabet")}</ToggleButton>
        </ToggleButtonGroup>
      </Box>
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
            <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.4)", mr: 0.25 }}>
              {t("graph.legend.nodes")}
            </Typography>
            {groupedNodeKinds.map(({ groupKey, kinds }) => (
              <React.Fragment key={`grp-${groupKey}`}>
                <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.45)", mr: 0.25 }}>
                  {t(`graph.legend.group.${groupKey}`)}
                </Typography>
                {kinds.map((kind) => renderNodeChip(kind, groupKey))}
              </React.Fragment>
            ))}
            {otherKinds.length > 0 ? (
              <React.Fragment key="grp-Other">
                <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.45)", mr: 0.25 }}>
                  {t("graph.legend.group.Other")}
                </Typography>
                {otherKinds.map((kind) => renderNodeChip(kind, "Other"))}
              </React.Fragment>
            ) : null}
          </>
        ) : null}
        {sortedEdgeTypes.length > 0 ? (
          <>
            <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.4)", ml: nodeTypes.length ? 1 : 0, mr: 0.25 }}>
              {t("graph.legend.edges")}
            </Typography>
            {sortedEdgeTypes.map((edgeType) => {
              const ec = edgeTypeCounts.get(edgeType) ?? 0;
              return (
                <Chip
                  key={`e-${edgeType}`}
                  icon={<ArrowForwardIcon sx={{ fontSize: "0.65rem !important", color: "rgba(255,255,255,0.45) !important" }} />}
                  label={`${localizeEdgeTypeKey(edgeType, t)} (${ec})`}
                  size="small"
                  variant="outlined"
                  sx={{
                    height: 22,
                    fontSize: "0.75rem",
                    borderColor: "rgba(255,255,255,0.14)",
                    color: "rgba(255,255,255,0.65)",
                    "& .MuiChip-icon": { marginLeft: "6px" },
                  }}
                />
              );
            })}
          </>
        ) : null}
      </Box>
    </Box>
  );
}
