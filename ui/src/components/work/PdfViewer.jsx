import React, { useCallback, useLayoutEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Tooltip from "@mui/material/Tooltip";
import { useTheme } from "@mui/material/styles";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import ZoomInIcon from "@mui/icons-material/ZoomIn";
import ZoomOutIcon from "@mui/icons-material/ZoomOut";
import { Document, Page, pdfjs } from "react-pdf";

import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { CursorIconButton } from "../common/index.js";
import { useI18n } from "../../i18n/useI18n.js";

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
  const tk = useTheme().appTokens;
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
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.75 }}>
        <Tooltip title={t("readerBody.pdfPrev")} enterDelay={400}>
          <span>
            <CursorIconButton
              type="button"
              disabled={page <= 1}
              aria-label={t("readerBody.pdfPrev")}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeftIcon sx={{ fontSize: "1.25rem" }} />
            </CursorIconButton>
          </span>
        </Tooltip>
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, minWidth: 72, textAlign: "center" }}>
          {t("readerBody.pdfPageOf", { page: String(page), total: String(numPages || "—") })}
        </Typography>
        <Tooltip title={t("readerBody.pdfNext")} enterDelay={400}>
          <span>
            <CursorIconButton
              type="button"
              disabled={!numPages || page >= numPages}
              aria-label={t("readerBody.pdfNext")}
              onClick={() => setPage((p) => (numPages ? Math.min(numPages, p + 1) : p))}
            >
              <ChevronRightIcon sx={{ fontSize: "1.25rem" }} />
            </CursorIconButton>
          </span>
        </Tooltip>
        <Box sx={{ flex: 1, minWidth: 8 }} />
        <Tooltip title={t("readerBody.pdfZoomOut")} enterDelay={400}>
          <span>
            <CursorIconButton
              type="button"
              aria-label={t("readerBody.pdfZoomOut")}
              onClick={() => setZoom((z) => Math.max(0.5, Math.round((z - 0.1) * 100) / 100))}
            >
              <ZoomOutIcon sx={{ fontSize: "1.1rem" }} />
            </CursorIconButton>
          </span>
        </Tooltip>
        <Typography
          sx={{ fontSize: "0.72rem", color: tk.text.secondary, minWidth: 40, textAlign: "center" }}
          aria-label="zoom"
        >
          {zoomLabel}
        </Typography>
        <Tooltip title={t("readerBody.pdfZoomIn")} enterDelay={400}>
          <span>
            <CursorIconButton
              type="button"
              aria-label={t("readerBody.pdfZoomIn")}
              onClick={() => setZoom((z) => Math.min(2.5, Math.round((z + 0.1) * 100) / 100))}
            >
              <ZoomInIcon sx={{ fontSize: "1.1rem" }} />
            </CursorIconButton>
          </span>
        </Tooltip>
      </Box>
      <Box
        ref={containerRef}
        sx={{
          minHeight: 480,
          border: `1px solid ${tk.border.default}`,
          borderRadius: "6px",
          backgroundColor: tk.surface.panelAlt,
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
              <Typography sx={{ fontSize: "0.8125rem", color: tk.text.secondary }}>{t("readerBody.pdfLoading")}</Typography>
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
