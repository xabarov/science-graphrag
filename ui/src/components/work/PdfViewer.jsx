import React, { useCallback, useLayoutEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import { Document, Page, pdfjs } from "react-pdf";

import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { CursorSmallButton } from "../common/index.js";
import { useI18n } from "../../i18n/I18nContext.jsx";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

/** Horizontal padding inside the scroll container; subtracted from page width. */
const PDF_HORIZONTAL_PADDING = 16;

/**
 * @param {{ fileUrl: string }} props
 */
export default function PdfViewer({ fileUrl }) {
  const { t } = useI18n();
  const [numPages, setNumPages] = useState(0);
  const [page, setPage] = useState(1);
  const [zoom, setZoom] = useState(1);
  const [loadError, setLoadError] = useState(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [prevFileUrl, setPrevFileUrl] = useState(fileUrl);
  const containerRef = useRef(null);

  if (prevFileUrl !== fileUrl) {
    setPrevFileUrl(fileUrl);
    setZoom(1);
    setPage(1);
    setNumPages(0);
    setLoadError(null);
  }

  const onLoadSuccess = useCallback((info) => {
    setLoadError(null);
    setNumPages(info.numPages || 0);
    setPage(1);
  }, []);

  const onLoadError = useCallback((err) => {
    const msg = err?.message || String(err);
    if (import.meta.env?.DEV) {
      // eslint-disable-next-line no-console -- intentional diagnostics for PDF worker / URL issues
      console.error("[PdfViewer] load error", err);
    }
    setLoadError(msg);
  }, []);

  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return undefined;
    const measure = () => {
      const inner = Math.max(0, el.clientWidth - PDF_HORIZONTAL_PADDING);
      setContainerWidth(inner);
    };
    measure();
    if (typeof ResizeObserver === "undefined") return undefined;
    const obs = new ResizeObserver(measure);
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  /** Hard caps protect very wide screens from giant pages and very narrow ones from rendering at 0px. */
  const baseWidth = containerWidth > 0 ? Math.min(1280, Math.max(280, containerWidth)) : 0;
  const pageWidth = baseWidth > 0 ? Math.round(baseWidth * zoom) : 0;

  const zoomLabel = `${Math.round(zoom * 100)}%`;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1, minWidth: 0 }}>
      {loadError ? (
        <Alert severity="warning" sx={{ fontSize: "0.8125rem" }}>
          {t("readerBody.pdfLoadError", { message: loadError })}
        </Alert>
      ) : null}
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1 }}>
        <CursorSmallButton type="button" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
          {t("readerBody.pdfPrev")}
        </CursorSmallButton>
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)" }}>
          {t("readerBody.pdfPageOf", { page: String(page), total: String(numPages || "—") })}
        </Typography>
        <CursorSmallButton
          type="button"
          disabled={!numPages || page >= numPages}
          onClick={() => setPage((p) => (numPages ? Math.min(numPages, p + 1) : p))}
        >
          {t("readerBody.pdfNext")}
        </CursorSmallButton>
        <Box sx={{ flex: 1 }} />
        <CursorSmallButton type="button" onClick={() => setZoom((z) => Math.max(0.5, Math.round((z - 0.1) * 100) / 100))}>
          {t("readerBody.pdfZoomOut")}
        </CursorSmallButton>
        <Typography
          sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.55)", minWidth: 38, textAlign: "center" }}
          aria-label="zoom"
        >
          {zoomLabel}
        </Typography>
        <CursorSmallButton type="button" onClick={() => setZoom((z) => Math.min(2.5, Math.round((z + 0.1) * 100) / 100))}>
          {t("readerBody.pdfZoomIn")}
        </CursorSmallButton>
      </Box>
      <Box
        ref={containerRef}
        sx={{
          maxHeight: "calc(100vh - 260px)",
          minHeight: 480,
          overflow: "auto",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: "6px",
          backgroundColor: "#1c1c1c",
          p: 1,
          display: "flex",
          justifyContent: "center",
        }}
      >
        <Document
          file={fileUrl}
          onLoadSuccess={onLoadSuccess}
          onLoadError={onLoadError}
          loading={
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 3, px: 2 }}>
              <CircularProgress size={22} />
              <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("readerBody.pdfLoading")}</Typography>
            </Box>
          }
        >
          {numPages && pageWidth > 0 ? (
            <Page pageNumber={page} width={pageWidth} renderAnnotationLayer renderTextLayer />
          ) : null}
        </Document>
      </Box>
    </Box>
  );
}
