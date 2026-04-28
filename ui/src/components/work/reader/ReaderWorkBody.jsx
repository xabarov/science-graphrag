import React, { lazy, Suspense, useEffect, useMemo, useRef } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import { useTheme } from "@mui/material/styles";

import { workPdfUrl } from "../../../services/researchApi.js";
import { describeTraceabilityState } from "../traceability/traceabilityState.js";
import { useI18n } from "../../../i18n/useI18n.js";
import ReaderChunkListPanel from "./ReaderChunkListPanel.jsx";
import ReaderMarkdownSourcePanel from "./ReaderMarkdownSourcePanel.jsx";
import ReaderPdfModeToggle from "./ReaderPdfModeToggle.jsx";
import ReaderTraceContextBanner from "./ReaderTraceContextBanner.jsx";
import ReaderWorkClaimsSection from "./ReaderWorkClaimsSection.jsx";
import ReaderWorkDetailCard from "./ReaderWorkDetailCard.jsx";
import { useReaderChunksState } from "./useReaderChunksState.js";
import { useReaderWorkData } from "./useReaderWorkData.js";

const PdfViewer = lazy(() => import("./PdfViewer.jsx"));

/**
 * Reader content for a fixed work_id (used by Reader tab and standalone Reader page).
 *
 * Layout: single column. Article metadata + abstract live in one compact card
 * above the body so the article text or PDF stays the focal point; chunks
 * advanced panel only appears when there are chunks to show.
 *
 * @param {{
 *   workId: string,
 *   workspaceId?: string,
 *   focusedFingerprint?: string,
 *   focusedSection?: string,
 *   citation?: string,
 *   onWorkMetaChange?: (meta: { title: string, loading: boolean, error: string }) => void,
 * }} props
 */
export default function ReaderWorkBody({
  workId,
  workspaceId = "",
  focusedFingerprint = "",
  focusedSection = "",
  citation = "",
  onWorkMetaChange,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const claimsUi = import.meta.env?.VITE_CLAIMS_ENABLED === "true";
  const { detail, chunks, extractedBodyPayload, loading, error, pdfAvailable, viewMode, setViewMode } =
    useReaderWorkData(workId);
  const { chunksOpen, setChunksOpen, orderedItems, combinedMarkdown, isChunkHighlighted } = useReaderChunksState(chunks, {
    focusedFingerprint,
    focusedSection,
  });
  const traceSummary = describeTraceabilityState({
    chunkFingerprint: focusedFingerprint,
    section: focusedSection,
    citation,
  });

  const hasEffectiveChunks = useMemo(() => {
    if (!chunks || loading) return false;
    const items = Array.isArray(chunks.items) ? chunks.items : [];
    const totalField = Number(chunks.total);
    const effectiveTotal = Number.isFinite(totalField) && totalField > 0 ? totalField : items.length;
    return effectiveTotal > 0;
  }, [chunks, loading]);

  const chunksBackendError = !loading && chunks && typeof chunks.error === "string" && chunks.error.trim() ? chunks.error.trim() : "";

  const abstractText =
    detail && typeof detail.abstract === "string" && detail.abstract.trim() ? detail.abstract : "";
  const extractedBodyText =
    extractedBodyPayload &&
    extractedBodyPayload.available === true &&
    typeof extractedBodyPayload.text === "string" &&
    extractedBodyPayload.text.trim()
      ? extractedBodyPayload.text.trim()
      : "";
  const useExtractedFileAsBody =
    !loading &&
    Boolean(chunks) &&
    !hasEffectiveChunks &&
    Boolean(extractedBodyText) &&
    viewMode === "ocr";
  /**
   * When the work has no extracted chunks but ships an abstract, surface the abstract as the
   * markdown body instead of leaving the column empty (otherwise the user has nothing to read
   * unless they switch to PDF). The metadata card hides its abstract toggle in that case.
   */
  const useAbstractAsBody =
    !loading &&
    Boolean(chunks) &&
    !hasEffectiveChunks &&
    !useExtractedFileAsBody &&
    Boolean(abstractText) &&
    viewMode === "ocr";

  /**
   * ADR 022: full-text reading prefers canonical ingest artifacts (`extracted-body`)
   * over Qdrant chunk joins when both exist. Chunk list below remains the
   * index-aligned traceability surface.
   */
  const preferCanonicalExtractedBody =
    !loading &&
    viewMode === "ocr" &&
    Boolean(chunks) &&
    hasEffectiveChunks &&
    Boolean(extractedBodyText);

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

  /**
   * Reader page already shows the title in the page header, so the metadata
   * card hides it; the workspace tab still renders the heading separately.
   * When the abstract is rendered as the body, the toggle in the card is
   * hidden to avoid showing the same text twice.
   */
  const detailCard =
    detail && !loading ? (
      <ReaderWorkDetailCard
        key={workId}
        detail={detail}
        defaultAbstractExpanded={false}
        hideAbstract={useAbstractAsBody}
      />
    ) : null;

  const showTraceBanner = traceSummary.length > 0;
  const showChunksPanel = Boolean(chunks) && !loading && hasEffectiveChunks;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
      {loading ? (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 2 }}>
          <CircularProgress size={22} sx={{ color: tk.accent.fg }} />
          <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted }}>{t("readerBody.loading")}</Typography>
        </Box>
      ) : null}
      {error ? (
        <Alert severity="error" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {error}
        </Alert>
      ) : null}

      {chunksBackendError ? (
        <Alert severity="warning" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {t("readerBody.chunksBackendError", { code: chunksBackendError })}
        </Alert>
      ) : null}

      {detailCard}

      {detail && !loading && pdfAvailable ? (
        <ReaderPdfModeToggle viewMode={viewMode} onViewModeChange={setViewMode} />
      ) : null}

      {chunks && !loading && viewMode === "pdf" && pdfAvailable ? (
        <Box sx={{ mb: 2 }}>
          <Suspense
            fallback={
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 2 }}>
                <CircularProgress size={22} />
                <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted }}>{t("readerBody.pdfLoading")}</Typography>
              </Box>
            }
          >
            <PdfViewer fileUrl={workPdfUrl(workId)} />
          </Suspense>
        </Box>
      ) : null}

      {chunks && !loading && viewMode === "ocr" && preferCanonicalExtractedBody ? (
        <ReaderMarkdownSourcePanel
          combinedMarkdown={extractedBodyText}
          sourceVariant="extractedFile"
          apiTruncated={extractedBodyPayload?.truncated === true}
        />
      ) : null}

      {chunks && !loading && viewMode === "ocr" && combinedMarkdown && !preferCanonicalExtractedBody ? (
        <ReaderMarkdownSourcePanel combinedMarkdown={combinedMarkdown} chunks={chunks} sourceVariant="extracted" />
      ) : null}

      {useExtractedFileAsBody ? (
        <ReaderMarkdownSourcePanel
          combinedMarkdown={extractedBodyText}
          sourceVariant="extractedFile"
          apiTruncated={extractedBodyPayload?.truncated === true}
        />
      ) : null}

      {useAbstractAsBody ? (
        <ReaderMarkdownSourcePanel combinedMarkdown={abstractText} sourceVariant="abstract" />
      ) : null}

      {chunks &&
      !loading &&
      viewMode === "ocr" &&
      !preferCanonicalExtractedBody &&
      !combinedMarkdown &&
      !useExtractedFileAsBody &&
      !useAbstractAsBody &&
      !pdfAvailable ? (
        <Alert severity="warning" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {t("readerBody.noExtractedTextOrPdf")}
        </Alert>
      ) : null}

      {claimsUi && detail && !loading ? <ReaderWorkClaimsSection workId={workId} /> : null}

      {showTraceBanner ? (
        <ReaderTraceContextBanner
          workId={workId}
          workspaceId={workspaceId}
          traceSummary={traceSummary}
          focusedFingerprint={focusedFingerprint}
          focusedSection={focusedSection}
          citation={citation}
        />
      ) : null}

      {showChunksPanel ? (
        <ReaderChunkListPanel
          chunks={chunks}
          chunksOpen={chunksOpen}
          setChunksOpen={setChunksOpen}
          orderedItems={orderedItems}
          isChunkHighlighted={isChunkHighlighted}
        />
      ) : null}
    </Box>
  );
}
