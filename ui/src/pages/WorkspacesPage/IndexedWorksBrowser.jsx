import React, { useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import TextField from "@mui/material/TextField";
import { InlineNotice } from "../../components/feedback/index.js";
import CircularProgress from "@mui/material/CircularProgress";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import ExpandMoreOutlinedIcon from "@mui/icons-material/ExpandMoreOutlined";
import SearchOutlinedIcon from "@mui/icons-material/SearchOutlined";
import TuneOutlinedIcon from "@mui/icons-material/TuneOutlined";

import WorkIdGlossaryHint from "../../components/layout/WorkIdGlossaryHint.jsx";
import { CursorIconAction, CursorPrimaryButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";

/**
 * @param {{
 *   q: string,
 *   onQChange: (v: string) => void,
 *   onSearch: (e: React.FormEvent) => void,
 *   loading: boolean,
 *   loadingMore: boolean,
 *   error: string | null,
 *   items: any[],
 *   total: number,
 *   canLoadMore: boolean,
 *   onLoadMore: () => void,
 *   sortBy: string,
 *   onSortByChange: (v: string) => void,
 *   viewDensity: string,
 *   onViewDensityChange: (v: string) => void,
 *   semanticFilter: string,
 *   onSemanticFilterChange: (v: string) => void,
 *   yearMin: string,
 *   yearMax: string,
 *   onYearMinChange: (v: string) => void,
 *   onYearMaxChange: (v: string) => void,
 *   sortedItems: any[],
 *   renderWorkRow: (w: any) => React.ReactNode,
 * }} props
 */
export default function IndexedWorksBrowser({
  q,
  onQChange,
  onSearch,
  loading,
  loadingMore,
  error,
  items,
  total,
  canLoadMore,
  onLoadMore,
  sortBy,
  onSortByChange,
  viewDensity,
  onViewDensityChange,
  semanticFilter,
  onSemanticFilterChange,
  yearMin,
  yearMax,
  onYearMinChange,
  onYearMaxChange,
  sortedItems,
  renderWorkRow,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const [extraFiltersOpen, setExtraFiltersOpen] = useState(false);

  const extraFiltersActive =
    semanticFilter !== "all" || yearMin.trim() !== "" || yearMax.trim() !== "" || viewDensity !== "compact";

  return (
    <Accordion
      defaultExpanded
      disableGutters
      sx={{
        mb: 2,
        backgroundColor: tk.surface.sidebar,
        border: `1px solid ${tk.border.default}`,
        borderRadius: "6px",
        "&:before": { display: "none" },
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreOutlinedIcon sx={{ color: tk.text.muted }} />}
        sx={{ px: 1.5, py: 0.75, minHeight: 44, "& .MuiAccordionSummary-content": { my: 0.5, alignItems: "center" } }}
      >
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1, width: "100%", minWidth: 0 }}>
          <Typography sx={{ fontSize: "0.8125rem", fontWeight: 600, color: tk.text.primary, flex: 1, minWidth: 0 }} noWrap>
            {t("workspaces.accordion.title")}
          </Typography>
          <Chip label={t("workspaces.totalIndex", { total })} size="small" sx={{ height: 22, fontSize: "0.6875rem", flexShrink: 0 }} />
        </Box>
      </AccordionSummary>
      <AccordionDetails sx={{ pt: 0, px: 1.5, pb: 1.5 }}>
        <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, lineHeight: 1.45, mb: 1 }}>
          <WorkIdGlossaryHint variant="corpus" />
        </Typography>
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, mb: 1.25 }}>{t("workspaces.accordion.desc")}</Typography>

        <Box component="form" onSubmit={onSearch} sx={{ mb: 1.25 }}>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
            <TextField
              label={t("workspaces.search.label")}
              value={q}
              onChange={(ev) => onQChange(ev.target.value)}
              size="small"
              sx={{
                flex: "1 1 200px",
                minWidth: 160,
                maxWidth: { sm: 420 },
                "& .MuiInputBase-input": { fontSize: "0.8125rem" },
                "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: tk.text.secondary },
              }}
            />
            <CursorIconAction type="submit" title={t("workspaces.search.submit")} disabled={loading}>
              <SearchOutlinedIcon sx={{ fontSize: "1.05rem" }} />
            </CursorIconAction>
            <FormControl size="small" sx={{ minWidth: 140, flex: "0 1 auto" }}>
              <InputLabel id="ws-sort">{t("workspaces.sort.label")}</InputLabel>
              <Select labelId="ws-sort" label={t("workspaces.sort.label")} value={sortBy} onChange={(e) => onSortByChange(e.target.value)}>
                <MenuItem value="api">{t("workspaces.sort.api")}</MenuItem>
                <MenuItem value="title">{t("workspaces.sort.titleAz")}</MenuItem>
                <MenuItem value="year_desc">{t("workspaces.sort.yearNewest")}</MenuItem>
              </Select>
            </FormControl>
            <CursorIconAction
              type="button"
              title={extraFiltersOpen ? t("workspaces.indexed.hideExtraFilters") : t("workspaces.indexed.showExtraFilters")}
              onClick={() => setExtraFiltersOpen((o) => !o)}
              sx={
                extraFiltersActive && !extraFiltersOpen
                  ? { borderColor: tk.accent.softBorder, color: tk.accent.fg }
                  : undefined
              }
            >
              <TuneOutlinedIcon sx={{ fontSize: "1.05rem" }} />
            </CursorIconAction>
          </Box>

          <Collapse in={extraFiltersOpen} timeout="auto" unmountOnExit>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))", md: "repeat(3, minmax(0, 1fr))" },
                gap: 1,
                mt: 1,
                pt: 1,
                borderTop: `1px solid ${tk.border.default}`,
              }}
            >
              <FormControl size="small" sx={{ minWidth: 0 }}>
                <InputLabel id="ws-view">{t("workspaces.view.label")}</InputLabel>
                <Select labelId="ws-view" label={t("workspaces.view.label")} value={viewDensity} onChange={(e) => onViewDensityChange(e.target.value)}>
                  <MenuItem value="cards">{t("workspaces.view.cards")}</MenuItem>
                  <MenuItem value="compact">{t("workspaces.view.compact")}</MenuItem>
                </Select>
              </FormControl>
              <FormControl size="small" sx={{ minWidth: 0 }}>
                <InputLabel id="ws-sem">{t("workspaces.semantic.label")}</InputLabel>
                <Select labelId="ws-sem" label={t("workspaces.semantic.label")} value={semanticFilter} onChange={(e) => onSemanticFilterChange(e.target.value)}>
                  <MenuItem value="all">{t("workspaces.semantic.all")}</MenuItem>
                  <MenuItem value="ready">{t("workspaces.semantic.ready")}</MenuItem>
                  <MenuItem value="not_ready">{t("workspaces.semantic.notReady")}</MenuItem>
                </Select>
              </FormControl>
              <Box sx={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 1 }}>
                <TextField label={t("workspaces.yearMin")} value={yearMin} onChange={(e) => onYearMinChange(e.target.value)} size="small" type="number" sx={{ minWidth: 0 }} />
                <TextField label={t("workspaces.yearMax")} value={yearMax} onChange={(e) => onYearMaxChange(e.target.value)} size="small" type="number" sx={{ minWidth: 0 }} />
              </Box>
            </Box>
          </Collapse>
        </Box>

        {loading && (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 2 }}>
            <CircularProgress size={22} sx={{ color: tk.accent.fg }} />
            <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted }}>{t("workspaces.loadingWorks")}</Typography>
          </Box>
        )}
        {error && (
          <InlineNotice severity="error" sx={{ mb: 2 }}>
            {error}
          </InlineNotice>
        )}

        {!loading && !error && (
          <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, mb: 1 }}>
            {t("workspaces.totalIndex", { total })}
            {items.length < total ? t("workspaces.loadedPartial", { loaded: items.length }) : null}
          </Typography>
        )}

        {!loading && !error && sortedItems.length === 0 ? (
          <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted, py: 1 }}>
            {t("workspaces.indexed.empty")}
          </Typography>
        ) : (
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: viewDensity === "cards" ? { xs: "1fr", lg: "repeat(2, minmax(0, 1fr))" } : "1fr",
              gap: 1,
            }}
          >
            {sortedItems.map(renderWorkRow)}
          </Box>
        )}

        {!loading && !error && canLoadMore ? (
          <Box sx={{ mt: 2 }}>
            <CursorPrimaryButton type="button" disabled={loadingMore} onClick={() => onLoadMore().catch(() => {})}>
              {loadingMore ? t("workspaces.loadMoreLoading") : t("workspaces.loadMore")}
            </CursorPrimaryButton>
          </Box>
        ) : null}
      </AccordionDetails>
    </Accordion>
  );
}
