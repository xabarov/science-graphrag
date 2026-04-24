import React from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Alert from "@mui/material/Alert";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";

import { CursorPrimaryButton, CursorSmallButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/I18nContext.jsx";
import { workAskUrl, workEvidenceUrl, workGraphUrl, workReaderUrl } from "./workspacePageUrls.js";

/**
 * @param {{ workId: string, title: string, year?: number | null, doi?: string | null, arxivId?: string | null, loading?: boolean, error?: string | null, workspaceId?: string, selected?: boolean, onCardActivate?: (workId: string) => void, cardRef?: React.Ref<HTMLDivElement | null> }} props
 */
export default function WorkPaperCard({
  workId,
  title,
  year,
  doi,
  arxivId,
  loading,
  error,
  workspaceId,
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
        if (e.target instanceof Element && e.target.closest("a")) return;
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
        maxWidth: 720,
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
          <Typography sx={{ fontWeight: 600, fontSize: "0.9375rem", color: "rgba(255,255,255,0.9)" }}>
            {title || t("workspace.paper.noTitle")}
          </Typography>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.5, fontFamily: "monospace" }}>
            {workId}
          </Typography>
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
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.42)", mt: 1.25 }}>
            {t("workspace.paper.hint")}{" "}
            <code style={{ fontSize: "0.7rem" }}>work_id</code>.
            {onCardActivate ? ` ${t("workspace.paper.hintSuffix")}` : ""}
          </Typography>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mt: 1.25 }}>
            <CursorPrimaryButton component={Link} to={workReaderUrl(workId)} sx={{ textDecoration: "none", fontSize: "0.8125rem" }}>
              {t("workspace.paper.reader")}
            </CursorPrimaryButton>
            <CursorSmallButton component={Link} to={workGraphUrl(workId, workspaceId)} sx={{ textDecoration: "none" }}>
              {t("workspace.paper.graph")}
            </CursorSmallButton>
            <CursorSmallButton component={Link} to={workAskUrl(workId, workspaceId)} sx={{ textDecoration: "none" }}>
              {t("workspace.paper.ask")}
            </CursorSmallButton>
            <CursorSmallButton component={Link} to={workEvidenceUrl(workId, workspaceId)} sx={{ textDecoration: "none" }}>
              {t("workspace.paper.evidence")}
            </CursorSmallButton>
          </Box>
        </>
      ) : null}
    </Box>
  );
}
