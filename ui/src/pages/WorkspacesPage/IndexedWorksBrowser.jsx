import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import { InlineNotice } from "../../components/feedback/index.js";
import CircularProgress from "@mui/material/CircularProgress";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import ExpandMoreOutlinedIcon from "@mui/icons-material/ExpandMoreOutlined";
import SearchOutlinedIcon from "@mui/icons-material/SearchOutlined";

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
      <AccordionSummary
        expandIcon={<ExpandMoreOutlinedIcon sx={{ color: "rgba(255,255,255,0.55)" }} />}
        sx={{ px: 1.5, py: 0.35 }}
      >
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1, width: "100%" }}>
          <Box sx={{ minWidth: 0 }}>
            <Typography sx={{ fontSize: "0.8125rem", fontWeight: 600, color: "rgba(255,255,255,0.9)" }}>
              {t("workspaces.accordion.title")}
            </Typography>
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mt: 0.4 }}>
              {t("workspaces.accordion.desc")}
            </Typography>
          </Box>
          <Chip label={t("workspaces.totalIndex", { total })} size="small" sx={{ height: 24, fontSize: "0.6875rem", flexShrink: 0 }} />
        </Box>
      </AccordionSummary>
      <AccordionDetails sx={{ pt: 0, px: 1.5, pb: 1.5 }}>
        <Box component="form" onSubmit={onSearch} sx={{ mb: 1.5 }}>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1.3fr) minmax(0, 1fr)" },
              gap: 1,
              alignItems: "stretch",
            }}
          >
            <Box
              sx={{
                display: "flex",
                gap: 0.75,
                alignItems: "center",
                minWidth: 0,
                p: 0.75,
                borderRadius: "6px",
                border: "1px solid rgba(255,255,255,0.08)",
                backgroundColor: "rgba(255,255,255,0.02)",
              }}
            >
              <TextField
                label={t("workspaces.search.label")}
                value={q}
                onChange={(ev) => onQChange(ev.target.value)}
                size="small"
                fullWidth
                sx={{
                  minWidth: 0,
                  "& .MuiInputBase-input": { fontSize: "0.8125rem" },
                  "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
                }}
              />
              <CursorIconAction type="submit" title={t("workspaces.search.submit")} disabled={loading}>
                <SearchOutlinedIcon sx={{ fontSize: "1.05rem" }} />
              </CursorIconAction>
            </Box>

            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "repeat(2, minmax(0, 1fr))", xl: "repeat(4, minmax(0, 1fr))" },
                gap: 1,
              }}
            >
              <FormControl size="small" sx={{ minWidth: 0 }}>
                <InputLabel id="ws-sort">{t("workspaces.sort.label")}</InputLabel>
                <Select labelId="ws-sort" label={t("workspaces.sort.label")} value={sortBy} onChange={(e) => onSortByChange(e.target.value)}>
                  <MenuItem value="api">{t("workspaces.sort.api")}</MenuItem>
                  <MenuItem value="title">{t("workspaces.sort.titleAz")}</MenuItem>
                  <MenuItem value="year_desc">{t("workspaces.sort.yearNewest")}</MenuItem>
                </Select>
              </FormControl>
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
          </Box>
        </Box>

        {loading && (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 2 }}>
            <CircularProgress size={22} sx={{ color: "rgba(129,140,248,0.9)" }} />
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("workspaces.loadingWorks")}</Typography>
          </Box>
        )}
        {error && (
          <InlineNotice severity="error" sx={{ mb: 2 }}>
            {error}
          </InlineNotice>
        )}

        {!loading && !error && (
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 1 }}>
            {t("workspaces.totalIndex", { total })}
            {items.length < total ? t("workspaces.loadedPartial", { loaded: items.length }) : null}
          </Typography>
        )}

        {!loading && !error && sortedItems.length === 0 ? (
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)", py: 1 }}>
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
