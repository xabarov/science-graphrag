import React, { useMemo } from "react";
import BusinessOutlinedIcon from "@mui/icons-material/BusinessOutlined";
import ClearIcon from "@mui/icons-material/Clear";
import MyLocationOutlinedIcon from "@mui/icons-material/MyLocationOutlined";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorIconButton } from "../../common/index.js";
import { useI18n } from "../../../i18n/useI18n.js";
import { outlinedAppTextFieldSx } from "../../../theme/settingsFormSx.js";
import GraphNodesVisibilityMenu from "../toolbar/GraphNodesVisibilityMenu.jsx";
import GraphViewChips from "../toolbar/GraphViewChips.jsx";

/**
 * @param {{
 *   workspaceId?: string,
 *   stats: { works_count?: number, authors_count?: number, external_citations?: number } | null,
 *   visibility: import("../model/graphVisibilityFilter.js").GraphVisibilityValue,
 *   onVisibilityChange: (patch: Partial<import("../model/graphVisibilityFilter.js").GraphVisibilityValue>) => void,
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
 *   workGraphIncludeInstitutions?: boolean,
 *   onToggleWorkGraphIncludeInstitutions?: () => void,
 * }} props
 */
export default function WorkspaceGraphToolbar({
  workspaceId = "",
  contextWorkId = "",
  stats,
  visibility,
  onVisibilityChange,
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
  workGraphIncludeInstitutions = false,
  onToggleWorkGraphIncludeInstitutions,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const wid = String(workspaceId || "").trim();
  const ctxWork = String(contextWorkId || "").trim();
  const filtersEnabled = Boolean(wid);
  const nodesMenuEnabled = filtersEnabled || Boolean(ctxWork);

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

  const institutionChipSx = useMemo(
    () => (active) => ({
      height: 26,
      fontSize: "0.72rem",
      fontWeight: 500,
      textTransform: "none",
      borderColor: active ? tk.accent.emphasisHoverBorder : tk.border.strong,
      color: active ? tk.accent.fg : tk.text.secondary,
      backgroundColor: active ? tk.accent.chipReadyBg : "transparent",
      "& .MuiChip-icon": { color: "inherit" },
      "&:hover": {
        borderColor: active ? tk.accent.emphasisHoverBorder : tk.control.outlinedBorderHover,
        backgroundColor: active ? tk.accent.emphasisHoverBg : tk.control.outlinedBgHover,
      },
    }),
    [tk],
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
        {nodesMenuEnabled ? (
          <>
            <GraphNodesVisibilityMenu visibility={visibility} onChange={onVisibilityChange} t={t} />
            {canvasMode && onLocalFindChange ? (
              <Divider orientation="vertical" flexItem sx={{ borderColor: tk.border.default, alignSelf: "stretch", minHeight: 28 }} />
            ) : null}
          </>
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

        {nodesMenuEnabled || canvasMode ? (
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
        {ctxWork && onToggleWorkGraphIncludeInstitutions ? (
          <>
            <Divider orientation="vertical" flexItem sx={{ borderColor: tk.border.default, alignSelf: "stretch", minHeight: 28 }} />
            <Tooltip title={t("graph.wsToolbar.chipInstitutionsTooltip")}>
              <Chip
                size="small"
                variant="outlined"
                icon={<BusinessOutlinedIcon sx={{ fontSize: "1rem !important" }} />}
                label={t("graph.wsToolbar.chipInstitutions")}
                onClick={onToggleWorkGraphIncludeInstitutions}
                aria-pressed={workGraphIncludeInstitutions}
                aria-label={t("graph.wsToolbar.chipInstitutionsAria")}
                sx={institutionChipSx(workGraphIncludeInstitutions)}
              />
            </Tooltip>
          </>
        ) : null}

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
