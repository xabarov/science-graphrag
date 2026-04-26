import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";

import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import ChatBubbleOutlineOutlinedIcon from "@mui/icons-material/ChatBubbleOutlineOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import OpenInNewOutlinedIcon from "@mui/icons-material/OpenInNewOutlined";

import { CursorIconAction } from "../../../components/common/index.js";
import { formatResearchApiError, getWorkDetail } from "../../../services/researchApi.js";
import { buildWorkspacePath } from "../utils/workContext.js";
import { workChatUrl } from "../workspacePageUrls.js";
import { useI18n } from "../../../i18n/I18nContext.jsx";

/**
 * @param {{ workId: string }} props
 */
export default function OverviewTab({ workId }) {
  const { t } = useI18n();
  const [searchParams] = useSearchParams();
  const workspaceId = (searchParams.get("workspace_id") || "").trim();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!workId.trim()) {
      setDetail(null);
      setError(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getWorkDetail(workId);
        if (cancelled) return;
        setDetail(res.data);
      } catch (err) {
        if (cancelled) return;
        setError(formatResearchApiError(err));
        setDetail(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workId]);

  if (!workId.trim()) {
    return (
      <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("wsTab.overview.pickWork")}</Typography>
    );
  }

  return (
    <Box>
      {loading && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 2 }}>
          <CircularProgress size={22} sx={{ color: "rgba(129,140,248,0.9)" }} />
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("wsTab.overview.loading")}</Typography>
        </Box>
      )}
      {error && (
        <Alert severity="error" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {error}
        </Alert>
      )}

      {detail && !loading && (
        <>
          <Box sx={{ p: 1.5, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#1a1a1a", mb: 2 }}>
            <Typography sx={{ fontWeight: 600, fontSize: "0.9375rem" }}>{detail.title || t("wsTab.overview.noTitle")}</Typography>
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mt: 0.5 }}>
              {detail.year != null ? `${detail.year} · ` : ""}
              {detail.doi ? `DOI ${detail.doi} · ` : ""}
              {detail.arxiv_id ? `arXiv ${detail.arxiv_id}` : ""}
            </Typography>
            {detail.abstract ? (
              <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)", mt: 1.5, whiteSpace: "pre-wrap" }}>
                {detail.abstract}
              </Typography>
            ) : null}
            {detail.ingestion ? (
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 1 }}>
                {t("wsTab.overview.ingestionLine", {
                  docId: String(detail.ingestion.document_id ?? ""),
                  hasChunks: String(detail.ingestion.has_chunks),
                  semantic: String(detail.ingestion.has_semantic_layer),
                })}
              </Typography>
            ) : null}
          </Box>

          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 1 }}>{t("wsTab.overview.quickActions")}</Typography>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
            <CursorIconAction component={Link} to={buildWorkspacePath(workId, "reader")} title={t("wsTab.overview.readerTab")}>
              <MenuBookOutlinedIcon sx={{ fontSize: "1.05rem" }} />
            </CursorIconAction>
            <CursorIconAction component={Link} to={buildWorkspacePath(workId, "graph")} title={t("wsTab.overview.graphTab")}>
              <AccountTreeOutlinedIcon sx={{ fontSize: "1.05rem" }} />
            </CursorIconAction>
            <CursorIconAction component={Link} to={workChatUrl(workId, workspaceId)} title={t("wsTab.overview.askTab")}>
              <ChatBubbleOutlineOutlinedIcon sx={{ fontSize: "1.05rem" }} />
            </CursorIconAction>
            <CursorIconAction component={Link} to={buildWorkspacePath(workId, "evidence")} title={t("wsTab.overview.evidenceTab")}>
              <DescriptionOutlinedIcon sx={{ fontSize: "1.05rem" }} />
            </CursorIconAction>
            <CursorIconAction
              component={Link}
              to={`/graph?work_id=${encodeURIComponent(workId)}`}
              title={t("wsTab.overview.openGraphFull")}
            >
              <OpenInNewOutlinedIcon sx={{ fontSize: "1.05rem" }} />
            </CursorIconAction>
          </Box>

          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 2 }}>{t("wsTab.overview.graphNote")}</Typography>
        </>
      )}
    </Box>
  );
}
