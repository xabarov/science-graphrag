import React, { useCallback, useMemo } from "react";
import { useI18n } from "../../i18n/I18nContext.jsx";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";

import { getScienceGraphNodeTypeIcon } from "./graphCanvasStyle.js";

const NODE_TYPE_OPTIONS = ["Work", "Author", "Method", "Dataset", "Venue", "Institution"];

/** @param {string} suffix e.g. "Mode", "Depth", "IncludeExternal", "NodeTypes" */
export function graphToolbarLocalStorageKey(workspaceId, suffix) {
  return `workspaceGraph${suffix}:${String(workspaceId || "").trim()}`;
}

function lsKey(workspaceId, suffix) {
  return graphToolbarLocalStorageKey(workspaceId, suffix);
}

function readLs(workspaceId, key, fallback) {
  if (typeof window === "undefined") return fallback;
  try {
    const v = window.localStorage.getItem(lsKey(workspaceId, key));
    return v != null && String(v).trim() !== "" ? String(v) : fallback;
  } catch {
    return fallback;
  }
}

function writeLs(workspaceId, key, value) {
  try {
    window.localStorage.setItem(lsKey(workspaceId, key), String(value));
  } catch {
    /* ignore */
  }
}

/**
 * @param {{
 *   workspaceId: string,
 *   stats: { works_count?: number, authors_count?: number, external_citations?: number } | null,
 *   value: {
 *     mode: string,
 *     depth: number,
 *     includeExternal: boolean,
 *     nodeTypesCsv: string,
 *     externalMinInternalCiters: number,
 *   },
 *   onChange: (next: {
 *     mode: string,
 *     depth: number,
 *     includeExternal: boolean,
 *     nodeTypesCsv: string,
 *     externalMinInternalCiters: number,
 *   }) => void,
 * }} props
 */
export default function WorkspaceGraphToolbar({ workspaceId, stats, value, onChange }) {
  const { t } = useI18n();
  const wid = String(workspaceId || "").trim();

  const chipTypes = useMemo(() => {
    const csv = value.nodeTypesCsv || readLs(wid, "NodeTypes", "Work,Author");
    const parts = csv
      .split(/[,;]/)
      .map((s) => s.trim())
      .filter(Boolean);
    return new Set(parts.length ? parts : ["Work", "Author"]);
  }, [wid, value.nodeTypesCsv]);

  const persistMode = useCallback(
    (mode) => {
      writeLs(wid, "Mode", mode);
      onChange({ ...value, mode });
    },
    [onChange, value, wid],
  );

  const persistDepth = useCallback(
    (depth) => {
      writeLs(wid, "Depth", String(depth));
      onChange({ ...value, depth });
    },
    [onChange, value, wid],
  );

  const persistInclude = useCallback(
    (includeExternal) => {
      writeLs(wid, "IncludeExternal", includeExternal ? "1" : "0");
      onChange({
        ...value,
        includeExternal,
        externalMinInternalCiters: includeExternal ? 2 : 0,
      });
    },
    [onChange, value, wid],
  );

  const persistTypes = useCallback(
    (nextSet) => {
      const csv = [...nextSet].sort().join(",");
      writeLs(wid, "NodeTypes", csv);
      onChange({ ...value, nodeTypesCsv: csv });
    },
    [onChange, value, wid],
  );

  const toggleType = useCallback(
    (t) => {
      const n = new Set(chipTypes);
      if (n.has(t)) {
        if (n.size <= 1) return;
        n.delete(t);
      } else {
        n.add(t);
      }
      persistTypes(n);
    },
    [chipTypes, persistTypes],
  );

  const statsLine = useMemo(() => {
    if (!stats || typeof stats !== "object") return "";
    const w = stats.works_count;
    const a = stats.authors_count;
    const x = stats.external_citations;
    const parts = [];
    if (typeof w === "number") parts.push(t("graph.wsToolbar.statsWorks", { count: String(w) }));
    if (typeof a === "number") parts.push(t("graph.wsToolbar.statsAuthors", { count: String(a) }));
    if (typeof x === "number") parts.push(t("graph.wsToolbar.statsExtCites", { count: String(x) }));
    return parts.join(" · ");
  }, [stats, t]);

  if (!wid) return null;

  return (
    <Box
      sx={{
        mb: 1.5,
        p: 1,
        borderRadius: 1,
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "rgba(255,255,255,0.02)",
      }}
    >
      <Stack direction="row" flexWrap="wrap" alignItems="flex-start" gap={1} useFlexGap>
        <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.45)", width: "100%" }}>
          {t("graph.wsToolbar.title")}
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1, flex: 1, minWidth: 0 }}>
          <ToggleButtonGroup
            size="small"
            exclusive
            value={value.mode}
            onChange={(_, v) => v && persistMode(v)}
            sx={{ "& .MuiToggleButton-root": { fontSize: "0.7rem", py: 0.25, px: 0.75 } }}
          >
            <ToggleButton value="inner_only">{t("graph.wsToolbar.modeInner")}</ToggleButton>
            <ToggleButton value="union_1hop">{t("graph.wsToolbar.modeUnion1hop")}</ToggleButton>
            <ToggleButton value="semantic_layer">{t("graph.wsToolbar.modeSemantic")}</ToggleButton>
            <ToggleButton value="full">{t("graph.wsToolbar.modeFull")}</ToggleButton>
          </ToggleButtonGroup>
          <Divider orientation="vertical" flexItem sx={{ borderColor: "rgba(255,255,255,0.08)", alignSelf: "stretch", minHeight: 28 }} />
          <ToggleButtonGroup
            size="small"
            exclusive
            value={value.depth}
            onChange={(_, v) => v != null && persistDepth(v)}
            sx={{ "& .MuiToggleButton-root": { fontSize: "0.7rem", py: 0.25, px: 0.75 } }}
          >
            <ToggleButton value={1}>{t("graph.wsToolbar.depth1")}</ToggleButton>
            <ToggleButton value={2}>{t("graph.wsToolbar.depth2")}</ToggleButton>
          </ToggleButtonGroup>
          <Divider orientation="vertical" flexItem sx={{ borderColor: "rgba(255,255,255,0.08)", alignSelf: "stretch", minHeight: 28 }} />
          <FormControlLabel
            control={
              <Switch
                size="small"
                checked={Boolean(value.includeExternal)}
                onChange={(e) => persistInclude(e.target.checked)}
              />
            }
            label={
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.75)" }}>
                {t("graph.wsToolbar.external")}
              </Typography>
            }
            sx={{ mr: 0 }}
          />
          <Divider orientation="vertical" flexItem sx={{ borderColor: "rgba(255,255,255,0.08)", alignSelf: "stretch", minHeight: 28 }} />
          <Box sx={{ display: "flex", flexDirection: "column", gap: 0.35, minWidth: 0 }}>
            <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.4)", lineHeight: 1 }}>
              {t("graph.wsToolbar.nodeTypesLabel")}
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, alignItems: "center" }}>
              {NODE_TYPE_OPTIONS.map((nodeType) => {
                const TypeIcon = getScienceGraphNodeTypeIcon(nodeType);
                return (
                  <Chip
                    key={nodeType}
                    icon={
                      TypeIcon ? (
                        <TypeIcon sx={{ fontSize: "0.95rem !important", color: "inherit !important", opacity: 0.92 }} />
                      ) : undefined
                    }
                    label={t(`graph.wsToolbar.nodeType.${nodeType}`)}
                    size="small"
                    variant={chipTypes.has(nodeType) ? "filled" : "outlined"}
                    onClick={() => toggleType(nodeType)}
                    sx={{
                      height: 24,
                      fontSize: "0.68rem",
                      "& .MuiChip-icon": { marginLeft: "6px" },
                      ...(chipTypes.has(nodeType)
                        ? { backgroundColor: "rgba(99,102,241,0.2)", borderColor: "rgba(129,140,248,0.4)" }
                        : { borderColor: "rgba(255,255,255,0.15)" }),
                    }}
                  />
                );
              })}
            </Box>
          </Box>
        </Box>
        {statsLine ? (
          <Typography
            sx={{
              fontSize: "0.72rem",
              color: "rgba(255,255,255,0.5)",
              alignSelf: "center",
              ml: { xs: 0, md: "auto" },
              flexShrink: 0,
              width: { xs: "100%", md: "auto" },
              textAlign: { xs: "left", md: "right" },
            }}
          >
            {statsLine}
          </Typography>
        ) : null}
      </Stack>
    </Box>
  );
}
