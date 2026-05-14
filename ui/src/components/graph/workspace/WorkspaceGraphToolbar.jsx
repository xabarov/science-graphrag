import React, { useMemo } from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../../i18n/useI18n.js";
import { outlinedAppTextFieldSx } from "../../../theme/settingsFormSx.js";
import WorkspaceToolbarFiltersRow from "./WorkspaceToolbarFiltersRow.jsx";
import WorkspaceToolbarPanelsRow from "./WorkspaceToolbarPanelsRow.jsx";
import { buildWorkspaceToolbarStatsFragments, computeWorkspaceToolbarFlags } from "./workspaceToolbarModel.js";

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

  const { ctxWork, filtersEnabled, nodesMenuEnabled, useCompactToolbarRow } = useMemo(
    () => computeWorkspaceToolbarFlags(workspaceId, contextWorkId, dense, canvasMode),
    [workspaceId, contextWorkId, dense, canvasMode],
  );

  const statsFragments = useMemo(
    () => buildWorkspaceToolbarStatsFragments(stats, filtersEnabled, t),
    [filtersEnabled, stats, t],
  );

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

  const panelsRow = (
    <WorkspaceToolbarPanelsRow
      viewChipsProps={viewChipsProps}
      ctxWork={ctxWork}
      onToggleWorkGraphIncludeInstitutions={onToggleWorkGraphIncludeInstitutions}
      workGraphIncludeInstitutions={workGraphIncludeInstitutions}
      institutionChipSx={institutionChipSx}
      dividerSx={dividerSx}
      statsFragments={statsFragments}
      statsTypographySx={statsTypographySx}
      t={t}
    />
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
        <WorkspaceToolbarFiltersRow
          leadingSlot={leadingSlot}
          dividerSx={dividerSx}
          nodesMenuEnabled={nodesMenuEnabled}
          visibility={visibility}
          onVisibilityChange={onVisibilityChange}
          t={t}
          canvasMode={canvasMode}
          onLocalFindChange={onLocalFindChange}
          localFindQuery={localFindQuery}
          onLocalFindClear={onLocalFindClear}
          onFocusFirstMatch={onFocusFirstMatch}
          localFindFocusDisabled={localFindFocusDisabled}
          localFindFieldSx={localFindFieldSx}
          tk={tk}
          useCompactToolbarRow={useCompactToolbarRow}
          panelsRow={panelsRow}
        />

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
