import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";

import { CursorPrimaryButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/I18nContext.jsx";

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

  return (
    <Accordion
      defaultExpanded={false}
      disableGutters
      sx={{
        mb: 2,
        backgroundColor: "#141414",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: "6px",
        "&:before": { display: "none" },
      }}
    >
      <AccordionSummary sx={{ fontSize: "0.8125rem", fontWeight: 600, color: "rgba(255,255,255,0.85)" }}>
        {t("workspaces.accordion.title")}
      </AccordionSummary>
      <AccordionDetails sx={{ pt: 0 }}>
        <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)", mb: 1 }}>
          {t("workspaces.indexed.title")}
        </Typography>

        <Box component="form" onSubmit={onSearch} sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2, alignItems: "flex-start" }}>
          <TextField
            label={t("workspaces.search.label")}
            value={q}
            onChange={(ev) => onQChange(ev.target.value)}
            size="small"
            sx={{
              minWidth: { xs: "100%", sm: 240 },
              flex: { xs: "1 1 100%", sm: "0 1 auto" },
              "& .MuiInputBase-input": { fontSize: "0.8125rem" },
              "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
            }}
          />
          <CursorPrimaryButton type="submit" disabled={loading}>
            {t("workspaces.search.submit")}
          </CursorPrimaryButton>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel id="ws-sort">{t("workspaces.sort.label")}</InputLabel>
            <Select labelId="ws-sort" label={t("workspaces.sort.label")} value={sortBy} onChange={(e) => onSortByChange(e.target.value)}>
              <MenuItem value="api">{t("workspaces.sort.api")}</MenuItem>
              <MenuItem value="title">{t("workspaces.sort.titleAz")}</MenuItem>
              <MenuItem value="year_desc">{t("workspaces.sort.yearNewest")}</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel id="ws-view">{t("workspaces.view.label")}</InputLabel>
            <Select labelId="ws-view" label={t("workspaces.view.label")} value={viewDensity} onChange={(e) => onViewDensityChange(e.target.value)}>
              <MenuItem value="cards">{t("workspaces.view.cards")}</MenuItem>
              <MenuItem value="compact">{t("workspaces.view.compact")}</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel id="ws-sem">{t("workspaces.semantic.label")}</InputLabel>
            <Select labelId="ws-sem" label={t("workspaces.semantic.label")} value={semanticFilter} onChange={(e) => onSemanticFilterChange(e.target.value)}>
              <MenuItem value="all">{t("workspaces.semantic.all")}</MenuItem>
              <MenuItem value="ready">{t("workspaces.semantic.ready")}</MenuItem>
              <MenuItem value="not_ready">{t("workspaces.semantic.notReady")}</MenuItem>
            </Select>
          </FormControl>
          <TextField label={t("workspaces.yearMin")} value={yearMin} onChange={(e) => onYearMinChange(e.target.value)} size="small" type="number" sx={{ width: 100 }} />
          <TextField label={t("workspaces.yearMax")} value={yearMax} onChange={(e) => onYearMaxChange(e.target.value)} size="small" type="number" sx={{ width: 100 }} />
        </Box>

        {loading && (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 2 }}>
            <CircularProgress size={22} sx={{ color: "rgba(129,140,248,0.9)" }} />
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("workspaces.loadingWorks")}</Typography>
          </Box>
        )}
        {error && (
          <Alert severity="error" sx={{ mb: 2, fontSize: "0.8125rem" }}>
            {error}
          </Alert>
        )}

        {!loading && !error && (
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 1 }}>
            {t("workspaces.totalIndex", { total })}
            {items.length < total ? t("workspaces.loadedPartial", { loaded: items.length }) : null}
          </Typography>
        )}

        <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>{sortedItems.map(renderWorkRow)}</Box>

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
