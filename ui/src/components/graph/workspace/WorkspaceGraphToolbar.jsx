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
 *   dense?: boolean,
 *   leadingSlot?: import("react").ReactNode,
 * }} props
 *
 * `dense` — компактные отступы панели с родителя (compact/focus layout страницы).
 * Одна горизонтальная полоса (без секционных подписей зон) также включается при **canvasMode**,
 * даже если `dense` false (обычный workspace + canvas).
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
  dense = false,
  leadingSlot = null,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const wid = String(workspaceId || "").trim();
  const ctxWork = String(contextWorkId || "").trim();
  const filtersEnabled = Boolean(wid);
  const nodesMenuEnabled = filtersEnabled || Boolean(ctxWork);
  /** Single wrapped row: no stacked zone labels; used when canvas or parent dense layout. */
  const useCompactToolbarRow = dense || canvasMode;

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

  const statsTypographySx = useMemo(
    () => ({
      fontSize: "0.72rem",
      color: tk.text.muted,
      ml: { xs: 0, sm: 1 },
      flexShrink: 0,
      width: { xs: "100%", sm: "auto" },
      textAlign: "left",
    }),
    [tk.text.muted],
  );

  const localFindFieldSx = useMemo(() => {
    const field = outlinedAppTextFieldSx(tk);
    return {
      minWidth: 160,
      flex: "1 1 200px",
      maxWidth: 520,
      ...field,
      "& .MuiOutlinedInput-root": { ...field["& .MuiOutlinedInput-root"], fontSize: "0.8125rem" },
      "& .MuiOutlinedInput-input": { color: tk.text.primary },
    };
  }, [tk]);

  const dividerSx = useMemo(
    () => ({ borderColor: tk.border.default, alignSelf: "stretch", minHeight: 28 }),
    [tk.border.default],
  );

  const viewChipsProps = useMemo(
    () => ({
      detailsVisible,
      legendOpen,
      diagnosticsOpen,
      onToggleDetails,
      onToggleLegend,
      onToggleDiagnostics,
      showLegendChip: true,
      showDiagnosticsChip: !labMode,
      t,
    }),
    [
      detailsVisible,
      diagnosticsOpen,
      labMode,
      legendOpen,
      onToggleDetails,
      onToggleDiagnostics,
      onToggleLegend,
      t,
    ],
  );

  const statsBlock =
    statsFragments.length > 0 ? (
      <Typography component="span" sx={statsTypographySx}>
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
    ) : null;

  const institutionsBlock =
    ctxWork && onToggleWorkGraphIncludeInstitutions ? (
      <>
        <Divider orientation="vertical" flexItem sx={dividerSx} />
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
    ) : null;

  const panelsRow = (
    <>
      <GraphViewChips {...viewChipsProps} />
      {institutionsBlock}
      {statsBlock}
    </>
  );

  return (
    <Box
      sx={{
        mb: useCompactToolbarRow ? 0.75 : 1.5,
        p: useCompactToolbarRow ? 0.5 : 1,
        borderRadius: 1,
        border: `1px solid ${tk.border.default}`,
        backgroundColor: tk.surface.panelAlt,
      }}
    >
      {filtersEnabled && !useCompactToolbarRow ? (
        <Typography sx={{ fontSize: "0.68rem", color: tk.text.muted, width: "100%", mb: 0.75 }}>
          {t("graph.wsToolbar.title")}
        </Typography>
      ) : null}
      <Stack spacing={useCompactToolbarRow ? 0 : 1} useFlexGap>
        {!useCompactToolbarRow ? (
          <Typography
            sx={{
              fontSize: "0.62rem",
              color: tk.text.faint,
              fontWeight: 600,
              letterSpacing: "0.04em",
              width: "100%",
            }}
          >
            {t("graph.wsToolbar.zoneFilter")}
          </Typography>
        ) : null}
        <Stack
          direction="row"
          flexWrap="wrap"
          alignItems="center"
          gap={useCompactToolbarRow ? 0.5 : 1}
          useFlexGap
          aria-label={useCompactToolbarRow ? t("graph.wsToolbar.compactToolbarAria") : undefined}
        >
          {leadingSlot ? (
            <>
              {leadingSlot}
              <Divider orientation="vertical" flexItem sx={dividerSx} />
            </>
          ) : null}
          {nodesMenuEnabled ? (
            <>
              <GraphNodesVisibilityMenu visibility={visibility} onChange={onVisibilityChange} t={t} />
              {canvasMode && onLocalFindChange ? <Divider orientation="vertical" flexItem sx={dividerSx} /> : null}
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

          {useCompactToolbarRow ? (
            <>
              {nodesMenuEnabled || canvasMode ? <Divider orientation="vertical" flexItem sx={dividerSx} /> : null}
              {panelsRow}
            </>
          ) : null}
        </Stack>

        {!useCompactToolbarRow ? (
          <>
            <Typography
              sx={{
                fontSize: "0.62rem",
                color: tk.text.faint,
                fontWeight: 600,
                letterSpacing: "0.04em",
                width: "100%",
                mt: 0.25,
              }}
            >
              {t("graph.wsToolbar.zonePanels")}
            </Typography>
            <Stack direction="row" flexWrap="wrap" alignItems="center" gap={1} useFlexGap>
              {panelsRow}
            </Stack>
          </>
        ) : null}
      </Stack>
    </Box>
  );
}
