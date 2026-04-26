import React from "react";
import { Link } from "react-router-dom";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import CenterFocusStrongIcon from "@mui/icons-material/CenterFocusStrong";
import MenuBookIcon from "@mui/icons-material/MenuBook";
import Box from "@mui/material/Box";
import Alert from "@mui/material/Alert";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";

import { CopyIdButton, CursorIconAction } from "../../components/common/index.js";
import PageActionToolbar from "../../components/layout/PageActionToolbar.jsx";
import { useI18n } from "../../i18n/I18nContext.jsx";
import { workGraphUrl, workReaderUrl } from "./workspacePageUrls.js";

/**
 * @param {{ workId: string, title: string, year?: number | null, doi?: string | null, arxivId?: string | null, loading?: boolean, error?: string | null, selected?: boolean, onCardActivate?: (workId: string) => void, cardRef?: React.Ref<HTMLDivElement | null> }} props
 */
export default function WorkPaperCard({
  workId,
  title,
  year,
  doi,
  arxivId,
  loading,
  error,
  selected,
  onCardActivate,
  cardRef,
}) {
  const { t } = useI18n();
  return (
    <Box
      ref={cardRef}
      onClick={(e) => {
        if (!onCardActivate) return;
        if (e.target instanceof Element && e.target.closest("a,button")) return;
        onCardActivate(workId);
      }}
      onKeyDown={(e) => {
        if (!onCardActivate) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onCardActivate(workId);
        }
      }}
      role={onCardActivate ? "button" : undefined}
      tabIndex={onCardActivate ? 0 : undefined}
      sx={{
        p: 1.75,
        borderRadius: "6px",
        border: selected ? "1px solid rgba(129,140,248,0.55)" : "1px solid rgba(255,255,255,0.08)",
        backgroundColor: selected ? "rgba(99,102,241,0.12)" : "#1a1a1a",
        boxShadow: selected ? "0 0 0 2px rgba(129,140,248,0.35)" : "none",
        cursor: onCardActivate ? "pointer" : "default",
        outline: "none",
      }}
    >
      {loading ? (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 1 }}>
          <CircularProgress size={20} sx={{ color: "rgba(129,140,248,0.9)" }} />
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)" }}>{t("workspace.paper.loading")}</Typography>
        </Box>
      ) : null}
      {error ? (
        <Alert severity="error" sx={{ mb: 1.5, fontSize: "0.8125rem" }}>
          {error}
        </Alert>
      ) : null}
      {!loading && !error ? (
        <>
          <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 1, minWidth: 0 }}>
            <Typography sx={{ fontWeight: 600, fontSize: "0.9375rem", color: "rgba(255,255,255,0.9)", minWidth: 0, flex: 1 }}>
              {title || t("workspace.paper.noTitle")}
            </Typography>
          </Box>
          <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 0.75 }}>
            {year != null ? (
              <Chip label={t("workspace.paper.yearChip", { year: String(year) })} size="small" sx={{ height: 22, fontSize: "0.6875rem" }} />
            ) : null}
            {doi ? (
              <Chip
                label={t("workspace.paper.doiChip", { doi: `${String(doi).slice(0, 24)}…` })}
                size="small"
                sx={{ height: 22, fontSize: "0.6875rem" }}
              />
            ) : null}
            {arxivId ? <Chip label={`arXiv ${arxivId}`} size="small" sx={{ height: 22, fontSize: "0.6875rem" }} /> : null}
          </Box>
          <PageActionToolbar
            sx={{ mt: 1.25 }}
            groups={[
              [
                <CursorIconAction key="rd" component={Link} to={workReaderUrl(workId)} title={t("workspace.tooltip.reader")}>
                  <MenuBookIcon sx={{ fontSize: "1.05rem" }} />
                </CursorIconAction>,
                <CursorIconAction key="gr" component={Link} to={workGraphUrl(workId, null)} title={t("workspace.tooltip.workGraph")}>
                  <AccountTreeIcon sx={{ fontSize: "1.05rem" }} />
                </CursorIconAction>,
                ...(onCardActivate
                  ? [
                      <CursorIconAction
                        key="fc"
                        title={t("workspace.tooltip.focusPaper")}
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          onCardActivate(workId);
                        }}
                      >
                        <CenterFocusStrongIcon sx={{ fontSize: "1.05rem" }} />
                      </CursorIconAction>,
                    ]
                  : []),
              ],
            ]}
            tail={
              <CopyIdButton
                id={workId}
                tooltipCopy={t("workspace.tooltip.copyWorkId")}
                tooltipCopied={t("workspace.tooltip.copied")}
              />
            }
          />
        </>
      ) : null}
    </Box>
  );
}
