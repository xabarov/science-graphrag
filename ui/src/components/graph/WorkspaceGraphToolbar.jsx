import React, { useCallback, useMemo } from "react";
import ClearIcon from "@mui/icons-material/Clear";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import MyLocationOutlinedIcon from "@mui/icons-material/MyLocationOutlined";
import PublicOutlinedIcon from "@mui/icons-material/PublicOutlined";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorIconButton } from "../common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { outlinedAppTextFieldSx } from "../../theme/settingsFormSx.js";
import GraphNodeTypesMenu from "./toolbar/GraphNodeTypesMenu.jsx";
import GraphScopeMenu from "./toolbar/GraphScopeMenu.jsx";
import GraphViewChips from "./toolbar/GraphViewChips.jsx";

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
 *   workspaceId?: string,
 *   stats: { works_count?: number, authors_count?: number, external_citations?: number } | null,
 *   value: {
 *     mode: string,
 *     depth: number,
 *     includeExternal: boolean,
 *     nodeTypesCsv: string,
 *     externalMinInternalCiters: number,
 *     includeClaims?: boolean,
 *   },
 *   onChange: (next: {
 *     mode: string,
 *     depth: number,
 *     includeExternal: boolean,
 *     nodeTypesCsv: string,
 *     externalMinInternalCiters: number,
 *     includeClaims?: boolean,
 *   }) => void,
 *   contextWorkId?: string,
 *   canvasMode?: boolean,
 *   localFindQuery?: string,
 *   onLocalFindChange?: (ev: import("react").ChangeEvent<HTMLInputElement>) => void,
 *   onLocalFindClear?: () => void,
 *   onFocusFirstMatch?: () => void,
 *   localFindFocusDisabled?: boolean,
 *   detailsVisible?: boolean,
 *   legendOpen?: boolean,
 *   diagnosticsOpen?: boolean,
 *   onToggleDetails?: () => void,
 *   onToggleLegend?: () => void,
 *   onToggleDiagnostics?: () => void,
 *   labMode?: boolean,
 * }} props
 */
export default function WorkspaceGraphToolbar({
  workspaceId = "",
  contextWorkId = "",
  stats,
  value,
  onChange,
  canvasMode = false,
  localFindQuery = "",
  onLocalFindChange,
  onLocalFindClear,
  onFocusFirstMatch,
  localFindFocusDisabled = true,
  detailsVisible = true,
  legendOpen = true,
  diagnosticsOpen = false,
  onToggleDetails = () => {},
  onToggleLegend = () => {},
  onToggleDiagnostics = () => {},
  labMode = false,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const wid = String(workspaceId || "").trim();
  const ctxWork = String(contextWorkId || "").trim();
  const filtersEnabled = Boolean(wid);
  const claimsToggleEnabled = filtersEnabled || Boolean(ctxWork);

  const chipTypes = useMemo(() => {
    if (!filtersEnabled) return new Set(NODE_TYPE_OPTIONS);
    const csv = value.nodeTypesCsv || readLs(wid, "NodeTypes", "Work,Author");
    const parts = csv
      .split(/[,;]/)
      .map((s) => s.trim())
      .filter(Boolean);
    return new Set(parts.length ? parts : ["Work", "Author"]);
  }, [filtersEnabled, wid, value.nodeTypesCsv]);

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

  const persistIncludeClaims = useCallback(
    (includeClaims) => {
      if (wid) {
        writeLs(wid, "IncludeClaims", includeClaims ? "1" : "0");
      } else if (ctxWork) {
        try {
          window.localStorage.setItem(`graphWorkIncludeClaims:${ctxWork}`, includeClaims ? "1" : "0");
        } catch {
          /* ignore */
        }
      }
      onChange({ ...value, includeClaims });
    },
    [onChange, value, wid, ctxWork],
  );

  const toggleType = useCallback(
    (typeKey) => {
      const n = new Set(chipTypes);
      if (n.has(typeKey)) {
        if (n.size <= 1) return;
        n.delete(typeKey);
      } else {
        n.add(typeKey);
      }
      persistTypes(n);
    },
    [chipTypes, persistTypes],
  );

  const statsFragments = useMemo(() => {
    if (!stats || typeof stats !== "object" || !filtersEnabled) return [];
    const w = stats.works_count;
    const a = stats.authors_count;
    const x = stats.external_citations;
    const out = [];
    if (typeof w === "number") {
      out.push({
        key: "w",
        text: t("graph.wsToolbar.statsWorks", { count: String(w) }),
        tip: t("graph.wsToolbar.statsWorksTooltip"),
      });
    }
    if (typeof a === "number") {
      out.push({
        key: "a",
        text: t("graph.wsToolbar.statsAuthors", { count: String(a) }),
        tip: t("graph.wsToolbar.statsAuthorsTooltip"),
      });
    }
    if (typeof x === "number") {
      out.push({
        key: "x",
        text: t("graph.wsToolbar.statsExtCites", { count: String(x) }),
        tip: t("graph.wsToolbar.statsExtCitesTooltip"),
      });
    }
    return out;
  }, [filtersEnabled, stats, t]);

  const miniToggleSx = useMemo(
    () => ({
      "& .MuiToggleButton-root": {
        fontSize: "0.72rem",
        py: 0.15,
        px: 0.6,
        minWidth: 36,
        textTransform: "none",
        color: tk.text.muted,
        borderColor: tk.border.strong,
      },
      "& .MuiToggleButton-root.Mui-selected": {
        color: tk.accent.fg,
        backgroundColor: tk.accent.chipReadyBg,
      },
    }),
    [tk.accent.chipReadyBg, tk.accent.fg, tk.border.strong, tk.text.muted],
  );

  const localFindFieldSx = useMemo(() => {
    const field = outlinedAppTextFieldSx(tk);
    return {
      minWidth: 160,
      flex: "1 1 180px",
      maxWidth: 360,
      ...field,
      "& .MuiOutlinedInput-root": { ...field["& .MuiOutlinedInput-root"], fontSize: "0.8125rem" },
      "& .MuiOutlinedInput-input": { color: tk.text.primary },
    };
  }, [tk]);

  return (
    <Box
      sx={{
        mb: 1.5,
        p: 1,
        borderRadius: 1,
        border: `1px solid ${tk.border.default}`,
        backgroundColor: tk.surface.panelAlt,
      }}
    >
      {filtersEnabled ? (
        <Typography sx={{ fontSize: "0.68rem", color: tk.text.muted, width: "100%", mb: 0.75 }}>
          {t("graph.wsToolbar.title")}
        </Typography>
      ) : null}
      <Stack direction="row" flexWrap="wrap" alignItems="center" gap={1} useFlexGap>
        {filtersEnabled ? (
          <>
            <GraphScopeMenu value={value.mode} onChange={persistMode} t={t} />
            <Divider orientation="vertical" flexItem sx={{ borderColor: tk.border.default, alignSelf: "stretch", minHeight: 28 }} />
            <Stack direction="row" alignItems="center" gap={0.5} sx={{ flexShrink: 0 }}>
              <Typography sx={{ fontSize: "0.7rem", color: tk.text.muted, mr: 0.25 }}>
                {t("graph.wsToolbar.depthLabel")}
              </Typography>
              <ToggleButtonGroup
                size="small"
                exclusive
                value={value.depth}
                onChange={(_, v) => v != null && persistDepth(v)}
                sx={miniToggleSx}
              >
                <ToggleButton
                  value={1}
                  aria-label={t("graph.standaloneDepth.depth1Aria")}
                  title={t("graph.wsToolbar.depthTooltip1")}
                >
                  {t("graph.wsToolbar.depthValue1")}
                </ToggleButton>
                <ToggleButton
                  value={2}
                  aria-label={t("graph.standaloneDepth.depth2Aria")}
                  title={t("graph.wsToolbar.depthTooltip2")}
                >
                  {t("graph.wsToolbar.depthValue2")}
                </ToggleButton>
              </ToggleButtonGroup>
            </Stack>
            <Divider orientation="vertical" flexItem sx={{ borderColor: tk.border.default, alignSelf: "stretch", minHeight: 28 }} />
            <Tooltip title={t("graph.wsToolbar.externalTooltip")}>
              <FormControlLabel
                control={
                  <Switch
                    size="small"
                    checked={Boolean(value.includeExternal)}
                    onChange={(e) => persistInclude(e.target.checked)}
                  />
                }
                label={
                  <Stack direction="row" alignItems="center" gap={0.35} component="span">
                    <PublicOutlinedIcon sx={{ fontSize: "1rem", color: tk.text.secondary }} />
                    <Typography component="span" sx={{ fontSize: "0.75rem", color: tk.text.secondary }}>
                      {t("graph.wsToolbar.externalLabel")}
                    </Typography>
                  </Stack>
                }
                sx={{ mr: 0 }}
              />
            </Tooltip>
            <Divider orientation="vertical" flexItem sx={{ borderColor: tk.border.default, alignSelf: "stretch", minHeight: 28 }} />
            <GraphNodeTypesMenu selectedSet={chipTypes} onToggleType={toggleType} t={t} />
          </>
        ) : null}

        {claimsToggleEnabled ? (
          <>
            {filtersEnabled ? (
              <Divider orientation="vertical" flexItem sx={{ borderColor: tk.border.default, alignSelf: "stretch", minHeight: 28 }} />
            ) : null}
            <Tooltip title={t("graph.wsToolbar.includeClaimsTooltip")}>
              <FormControlLabel
                control={
                  <Switch
                    size="small"
                    checked={Boolean(value.includeClaims)}
                    onChange={(e) => persistIncludeClaims(e.target.checked)}
                  />
                }
                label={
                  <Stack direction="row" alignItems="center" gap={0.35} component="span">
                    <FactCheckOutlinedIcon sx={{ fontSize: "1rem", color: tk.text.secondary }} />
                    <Typography component="span" sx={{ fontSize: "0.75rem", color: tk.text.secondary }}>
                      {t("graph.wsToolbar.includeClaimsLabel")}
                    </Typography>
                  </Stack>
                }
                sx={{ mr: 0 }}
              />
            </Tooltip>
          </>
        ) : null}

        {filtersEnabled && canvasMode ? (
          <Divider orientation="vertical" flexItem sx={{ borderColor: tk.border.default, alignSelf: "stretch", minHeight: 28 }} />
        ) : null}

        {canvasMode && onLocalFindChange ? (
          <>
            <TextField
              size="small"
              variant="outlined"
              value={localFindQuery}
              onChange={onLocalFindChange}
              placeholder={t("graph.localFind.placeholder")}
              inputProps={{ "aria-label": t("graph.localFind.aria") }}
              sx={localFindFieldSx}
              InputProps={{
                endAdornment: localFindQuery && onLocalFindClear ? (
                  <InputAdornment position="end">
                    <IconButton
                      size="small"
                      aria-label={t("graph.localFind.clearAria")}
                      onClick={onLocalFindClear}
                      edge="end"
                      sx={{ color: tk.text.muted }}
                    >
                      <ClearIcon fontSize="small" />
                    </IconButton>
                  </InputAdornment>
                ) : null,
              }}
            />
            {onFocusFirstMatch ? (
              <Tooltip title={t("graph.localFind.focusFirstTooltip")}>
                <span>
                  <CursorIconButton
                    type="button"
                    aria-label={t("graph.localFind.focusFirst")}
                    onClick={onFocusFirstMatch}
                    disabled={localFindFocusDisabled}
                  >
                    <MyLocationOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                  </CursorIconButton>
                </span>
              </Tooltip>
            ) : null}
          </>
        ) : null}

        {filtersEnabled || canvasMode ? (
          <Divider orientation="vertical" flexItem sx={{ borderColor: tk.border.default, alignSelf: "stretch", minHeight: 28 }} />
        ) : null}
        <GraphViewChips
          detailsVisible={detailsVisible}
          legendOpen={legendOpen}
          diagnosticsOpen={diagnosticsOpen}
          onToggleDetails={onToggleDetails}
          onToggleLegend={onToggleLegend}
          onToggleDiagnostics={onToggleDiagnostics}
          showLegendChip
          showDiagnosticsChip={!labMode}
          t={t}
        />

        {statsFragments.length > 0 ? (
          <Typography
            component="span"
            sx={{
              fontSize: "0.72rem",
              color: tk.text.muted,
              ml: { xs: 0, md: "auto" },
              flexShrink: 0,
              width: { xs: "100%", md: "auto" },
              textAlign: { xs: "left", md: "right" },
            }}
          >
            {statsFragments.map((frag, i) => (
              <React.Fragment key={frag.key}>
                {i > 0 ? " · " : null}
                <Tooltip title={frag.tip}>
                  <Box component="span" sx={{ cursor: "default" }}>
                    {frag.text}
                  </Box>
                </Tooltip>
              </React.Fragment>
            ))}
          </Typography>
        ) : null}
      </Stack>
    </Box>
  );
}
