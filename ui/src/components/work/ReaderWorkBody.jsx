import React, { lazy, Suspense, useEffect, useRef } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";

import { workPdfUrl } from "../../services/researchApi.js";
import { describeTraceabilityState } from "./traceabilityState.js";
import { useI18n } from "../../i18n/I18nContext.jsx";
import ReaderChunkListPanel from "./ReaderChunkListPanel.jsx";
import ReaderMarkdownSourcePanel from "./ReaderMarkdownSourcePanel.jsx";
import ReaderPdfModeToggle from "./ReaderPdfModeToggle.jsx";
import ReaderShell from "./ReaderShell.jsx";
import ReaderSideRail from "./ReaderSideRail.jsx";
import ReaderTraceContextBanner from "./ReaderTraceContextBanner.jsx";
import ReaderWorkClaimsSection from "./ReaderWorkClaimsSection.jsx";
import ReaderWorkDetailCard from "./ReaderWorkDetailCard.jsx";
import { useReaderChunksState } from "./useReaderChunksState.js";
import { useReaderWorkData } from "./useReaderWorkData.js";

const PdfViewer = lazy(() => import("./PdfViewer.jsx"));

/**
 * Reader content for a fixed work_id (used by Reader tab and standalone Reader page).
 * @param {{
 *   workId: string,
 *   focusedFingerprint?: string,
 *   focusedSection?: string,
 *   citation?: string,
 *   layoutVariant?: "stack" | "readerPage",
 *   onWorkMetaChange?: (meta: { title: string, loading: boolean, error: string }) => void,
 * }} props
 */
export default function ReaderWorkBody({
  workId,
  focusedFingerprint = "",
  focusedSection = "",
  citation = "",
  layoutVariant = "stack",
  onWorkMetaChange,
}) {
  const { t } = useI18n();
  const claimsUi = import.meta.env?.VITE_CLAIMS_ENABLED === "true";
  const { detail, chunks, loading, error, pdfAvailable, viewMode, setViewMode } = useReaderWorkData(workId);
  const { chunksOpen, setChunksOpen, orderedItems, combinedMarkdown, isChunkHighlighted } = useReaderChunksState(chunks, {
    focusedFingerprint,
    focusedSection,
  });
  const traceSummary = describeTraceabilityState({
    chunkFingerprint: focusedFingerprint,
    section: focusedSection,
    citation,
  });

  const metaCbRef = useRef(onWorkMetaChange);
  useEffect(() => {
    metaCbRef.current = onWorkMetaChange;
  }, [onWorkMetaChange]);

  useEffect(() => {
    if (!onWorkMetaChange) return;
    const title = detail?.title != null ? String(detail.title) : "";
    metaCbRef.current?.({
      title,
      loading,
      error: error || "",
    });
  }, [detail?.title, loading, error, onWorkMetaChange]);

  const detailBlock = detail && !loading ? <ReaderWorkDetailCard detail={detail} /> : null;

  const core = (
    <>
      {loading ? (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 2 }}>
          <CircularProgress size={22} sx={{ color: "rgba(129,140,248,0.9)" }} />
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("readerBody.loading")}</Typography>
        </Box>
      ) : null}
      {error ? (
        <Alert severity="error" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {error}
        </Alert>
      ) : null}

      {layoutVariant === "stack" ? detailBlock : null}

      {detail && !loading && pdfAvailable ? (
        <ReaderPdfModeToggle viewMode={viewMode} onViewModeChange={setViewMode} />
      ) : null}

      {chunks && !loading && viewMode === "pdf" && pdfAvailable ? (
        <Box sx={{ mb: 2 }}>
          <Suspense
            fallback={
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 2 }}>
                <CircularProgress size={22} />
                <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("readerBody.pdfLoading")}</Typography>
              </Box>
            }
          >
            <PdfViewer fileUrl={workPdfUrl(workId)} />
          </Suspense>
        </Box>
      ) : null}

      {chunks && !loading && viewMode === "markdown" && combinedMarkdown ? (
        <ReaderMarkdownSourcePanel combinedMarkdown={combinedMarkdown} chunks={chunks} />
      ) : null}

      {chunks && !loading && viewMode === "markdown" && !combinedMarkdown && pdfAvailable ? (
        <Alert severity="info" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {t("readerBody.emptyMarkdownTryPdf")}
        </Alert>
      ) : null}

      {claimsUi && detail && !loading ? <ReaderWorkClaimsSection workId={workId} /> : null}

      {chunks && !loading ? (
        <>
          <ReaderTraceContextBanner
            workId={workId}
            traceSummary={traceSummary}
            focusedFingerprint={focusedFingerprint}
            focusedSection={focusedSection}
            citation={citation}
          />
          <ReaderChunkListPanel
            chunks={chunks}
            chunksOpen={chunksOpen}
            setChunksOpen={setChunksOpen}
            orderedItems={orderedItems}
            isChunkHighlighted={isChunkHighlighted}
          />
        </>
      ) : null}
    </>
  );

  if (layoutVariant === "readerPage") {
    return <ReaderShell main={<Box>{core}</Box>} rail={<ReaderSideRail>{detailBlock}</ReaderSideRail>} />;
  }

  return <Box>{core}</Box>;
}
