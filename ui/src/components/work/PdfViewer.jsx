import React, { useCallback, useState } from "react";
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

/**
 * @param {{ fileUrl: string }} props
 */
export default function PdfViewer({ fileUrl }) {
  const { t } = useI18n();
  const [numPages, setNumPages] = useState(0);
  const [page, setPage] = useState(1);
  const [scale, setScale] = useState(1.1);
  const [loadError, setLoadError] = useState(null);

  const onLoadSuccess = useCallback((info) => {
    setLoadError(null);
    setNumPages(info.numPages || 0);
    setPage(1);
  }, []);

  const onLoadError = useCallback((err) => {
    setLoadError(err?.message || String(err));
  }, []);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
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
        <CursorSmallButton type="button" onClick={() => setScale((s) => Math.min(2.2, Math.round((s + 0.15) * 100) / 100))}>
          {t("readerBody.pdfZoomIn")}
        </CursorSmallButton>
        <CursorSmallButton type="button" onClick={() => setScale((s) => Math.max(0.6, Math.round((s - 0.15) * 100) / 100))}>
          {t("readerBody.pdfZoomOut")}
        </CursorSmallButton>
      </Box>
      <Box
        sx={{
          maxHeight: "min(65vh, 640px)",
          overflow: "auto",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: "6px",
          backgroundColor: "#2a2a2a",
          p: 1,
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
          {numPages ? <Page pageNumber={page} scale={scale} renderAnnotationLayer renderTextLayer /> : null}
        </Document>
      </Box>
    </Box>
  );
}
