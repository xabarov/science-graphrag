import React, { lazy, Suspense, useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import { Link } from "react-router-dom";

import {
  formatResearchApiError,
  getWorkClaims,
  getWorkChunks,
  getWorkDetail,
  getWorkSources,
  workPdfUrl,
} from "../../services/researchApi.js";
import { CursorSmallButton } from "../common/index.js";
import { buildWorkspaceTracePath, describeTraceabilityState } from "./traceabilityState.js";
import { useI18n } from "../../i18n/I18nContext.jsx";

const PdfViewer = lazy(() => import("./PdfViewer.jsx"));

/**
 * Reader content for a fixed work_id (used by Reader tab and standalone Reader page).
 * @param {{ workId: string, focusedFingerprint?: string, focusedSection?: string, citation?: string }} props
 */
export default function ReaderWorkBody({
  workId,
  focusedFingerprint = "",
  focusedSection = "",
  citation = "",
}) {
  const { t } = useI18n();
  const [detail, setDetail] = useState(null);
  const [chunks, setChunks] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [chunksOpen, setChunksOpen] = useState(false);
  const claimsUi = import.meta.env?.VITE_CLAIMS_ENABLED === "true";
  const [claimsOpen, setClaimsOpen] = useState(false);
  const [claimsPayload, setClaimsPayload] = useState(null);
  const [claimsLoading, setClaimsLoading] = useState(false);
  const [claimsError, setClaimsError] = useState(null);
  const [claimTypeFilter, setClaimTypeFilter] = useState("all");
  const [polarityFilter, setPolarityFilter] = useState("all");
  const [sourcesPayload, setSourcesPayload] = useState(null);
  const [viewMode, setViewMode] = useState("markdown");
  const traceSummary = describeTraceabilityState({
    chunkFingerprint: focusedFingerprint,
    section: focusedSection,
    citation,
  });

  useEffect(() => {
    if (!workId.trim()) {
      setDetail(null);
      setChunks(null);
      setError(null);
      setSourcesPayload(null);
      setViewMode("markdown");
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      setViewMode("markdown");
      try {
        const [dRes, cRes, sRes] = await Promise.all([
          getWorkDetail(workId),
          getWorkChunks(workId, { limit: 200, offset: 0 }),
          getWorkSources(workId).catch(() => ({ data: null })),
        ]);
        if (cancelled) return;
        setDetail(dRes.data);
        setChunks(cRes.data);
        setSourcesPayload(sRes.data);
      } catch (err) {
        if (cancelled) return;
        setError(formatResearchApiError(err));
        setDetail(null);
        setChunks(null);
        setSourcesPayload(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workId]);

  useEffect(() => {
    if (!claimsUi || !claimsOpen || !workId.trim()) {
      return undefined;
    }
    let cancelled = false;
    (async () => {
      setClaimsLoading(true);
      setClaimsError(null);
      try {
        const res = await getWorkClaims(workId);
        if (cancelled) return;
        setClaimsPayload(res.data);
      } catch (err) {
        if (cancelled) return;
        setClaimsError(formatResearchApiError(err));
        setClaimsPayload(null);
      } finally {
        if (!cancelled) setClaimsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [claimsUi, claimsOpen, workId]);

  const pdfAvailable = useMemo(() => {
    const rows = sourcesPayload?.sources;
    if (!Array.isArray(rows)) return false;
    const pdf = rows.find((s) => s && String(s.repr || "").toLowerCase() === "pdf");
    return Boolean(pdf?.available);
  }, [sourcesPayload]);

  useEffect(() => {
    if (!pdfAvailable && viewMode === "pdf") setViewMode("markdown");
  }, [pdfAvailable, viewMode]);

  const combinedExtractedText = useMemo(() => {
    const items = chunks?.items;
    if (!Array.isArray(items) || !items.length) return "";
    const sorted = [...items].sort((a, b) => (Number(a.order) || 0) - (Number(b.order) || 0));
    return sorted
      .map((ch) => {
        const head = ch.section_path ? `## ${ch.section_path}\n\n` : "";
        return `${head}${ch.text || ""}`.trim();
      })
      .filter(Boolean)
      .join("\n\n---\n\n");
  }, [chunks]);

  const claimTypeOptions = useMemo(() => {
    const rows = claimsPayload?.items;
    if (!Array.isArray(rows)) return [];
    return [...new Set(rows.map((x) => String(x.claim_type || "").trim()).filter(Boolean))].sort();
  }, [claimsPayload]);

  const polarityOptions = useMemo(() => {
    const rows = claimsPayload?.items;
    if (!Array.isArray(rows)) return [];
    return [...new Set(rows.map((x) => String(x.polarity || "").trim()).filter(Boolean))].sort();
  }, [claimsPayload]);

  const filteredClaims = useMemo(() => {
    const rows = claimsPayload?.items;
    if (!Array.isArray(rows)) return [];
    return rows.filter((cl) => {
      const typeOk = claimTypeFilter === "all" || String(cl.claim_type || "") === claimTypeFilter;
      const polOk = polarityFilter === "all" || String(cl.polarity || "") === polarityFilter;
      return typeOk && polOk;
    });
  }, [claimsPayload, claimTypeFilter, polarityFilter]);

  return (
    <Box>
      {loading && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 2 }}>
          <CircularProgress size={22} sx={{ color: "rgba(129,140,248,0.9)" }} />
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("readerBody.loading")}</Typography>
        </Box>
      )}
      {error && (
        <Alert severity="error" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {error}
        </Alert>
      )}

      {detail && !loading && (
        <Box sx={{ mb: 2, p: 1.5, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#1a1a1a" }}>
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>{detail.title || t("readerBody.noTitle")}</Typography>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mt: 0.5 }}>
            {detail.year != null ? `${detail.year} · ` : ""}
            {detail.doi ? `DOI ${detail.doi} · ` : ""}
            {detail.arxiv_id ? `arXiv ${detail.arxiv_id}` : ""}
          </Typography>
          {detail.abstract && (
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)", mt: 1, whiteSpace: "pre-wrap" }}>
              {detail.abstract}
            </Typography>
          )}
          {detail.ingestion && (
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 1 }}>
              {t("readerBody.ingestionLine", {
                docId: String(detail.ingestion.document_id ?? ""),
                hasChunks: String(detail.ingestion.has_chunks),
                semantic: String(detail.ingestion.has_semantic_layer),
              })}
            </Typography>
          )}
        </Box>
      )}

      {detail && !loading && pdfAvailable ? (
        <Box sx={{ mb: 1.5, display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1 }}>
          <ToggleButtonGroup
            size="small"
            exclusive
            value={viewMode}
            onChange={(_e, v) => {
              if (v) setViewMode(v);
            }}
            sx={{
              "& .MuiToggleButton-root": {
                fontSize: "0.75rem",
                py: 0.25,
                px: 1,
                textTransform: "none",
              },
            }}
          >
            <ToggleButton value="markdown">{t("readerBody.viewMarkdown")}</ToggleButton>
            <ToggleButton value="pdf">{t("readerBody.viewPdf")}</ToggleButton>
          </ToggleButtonGroup>
        </Box>
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

      {chunks && !loading && viewMode === "markdown" && combinedExtractedText ? (
        <Box sx={{ mb: 2, p: 1.5, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#141414" }}>
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 1 }}>{t("readerBody.extractedTitle")}</Typography>
          <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.42)", mb: 1 }}>{t("readerBody.extractedHint")}</Typography>
          <Box
            sx={{
              maxHeight: "min(60vh, 520px)",
              overflow: "auto",
              p: 1.25,
              borderRadius: "4px",
              border: "1px solid rgba(255,255,255,0.06)",
              backgroundColor: "#0a0a0a",
            }}
          >
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.82)", whiteSpace: "pre-wrap" }}>
              {combinedExtractedText.length > 120_000 ? `${combinedExtractedText.slice(0, 120_000)}…` : combinedExtractedText}
            </Typography>
          </Box>
          {Number(chunks.total) > (chunks.items || []).length ? (
            <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.38)", mt: 0.75 }}>
              {t("readerBody.chunksPartial", { shown: String((chunks.items || []).length), total: String(chunks.total) })}
            </Typography>
          ) : null}
        </Box>
      ) : null}

      {chunks && !loading && viewMode === "markdown" && !combinedExtractedText && pdfAvailable ? (
        <Alert severity="info" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {t("readerBody.emptyMarkdownTryPdf")}
        </Alert>
      ) : null}

      {claimsUi && detail && !loading ? (
        <Box sx={{ mb: 2, p: 1.5, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#161616" }}>
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1, mb: 0.5 }}>
            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>{t("readerBody.claimsTitle")}</Typography>
            <CursorSmallButton type="button" onClick={() => setClaimsOpen((o) => !o)} sx={{ fontSize: "0.75rem" }}>
              {claimsOpen ? t("readerBody.hide") : t("readerBody.show")}
            </CursorSmallButton>
          </Box>
          <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.42)", mb: 1 }}>{t("readerBody.claimsHint")}</Typography>
          <Collapse in={claimsOpen}>
            {claimsLoading ? (
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 1 }}>
                <CircularProgress size={20} sx={{ color: "rgba(129,140,248,0.9)" }} />
                <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}>{t("readerBody.claimsLoading")}</Typography>
              </Box>
            ) : null}
            {claimsError ? (
              <Alert severity="warning" sx={{ fontSize: "0.75rem" }}>
                {claimsError}
              </Alert>
            ) : null}
            {claimsPayload && Array.isArray(claimsPayload.items) ? (
              claimsPayload.items.length === 0 ? (
                <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}>{t("readerBody.claimsEmpty")}</Typography>
              ) : (
                <Box sx={{ display: "flex", flexDirection: "column", gap: 1.25, mt: 0.5 }}>
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 0.25 }}>
                    <ToggleButtonGroup
                      size="small"
                      exclusive
                      value={claimTypeFilter}
                      onChange={(_e, v) => {
                        if (v) setClaimTypeFilter(v);
                      }}
                      sx={{ "& .MuiToggleButton-root": { fontSize: "0.7rem", py: 0.15, px: 0.8, textTransform: "none" } }}
                    >
                      <ToggleButton value="all">{t("readerBody.claimFilterAllTypes")}</ToggleButton>
                      {claimTypeOptions.map((opt) => (
                        <ToggleButton key={`ct-${opt}`} value={opt}>
                          {opt}
                        </ToggleButton>
                      ))}
                    </ToggleButtonGroup>
                    <ToggleButtonGroup
                      size="small"
                      exclusive
                      value={polarityFilter}
                      onChange={(_e, v) => {
                        if (v) setPolarityFilter(v);
                      }}
                      sx={{ "& .MuiToggleButton-root": { fontSize: "0.7rem", py: 0.15, px: 0.8, textTransform: "none" } }}
                    >
                      <ToggleButton value="all">{t("readerBody.claimFilterAllPolarities")}</ToggleButton>
                      {polarityOptions.map((opt) => (
                        <ToggleButton key={`cp-${opt}`} value={opt}>
                          {opt}
                        </ToggleButton>
                      ))}
                    </ToggleButtonGroup>
                  </Box>
                  {filteredClaims.length === 0 ? (
                    <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}>
                      {t("readerBody.claimsNoFilterMatch")}
                    </Typography>
                  ) : null}
                  {filteredClaims.map((cl) => (
                    <Box
                      key={cl.claim_id}
                      sx={{
                        p: 1.25,
                        borderRadius: "6px",
                        border: "1px solid rgba(255,255,255,0.07)",
                        backgroundColor: "#101010",
                      }}
                    >
                      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mb: 0.5 }}>
                        <Chip label={cl.claim_type || "—"} size="small" sx={{ height: 22, fontSize: "0.65rem" }} />
                        <Chip label={cl.polarity || "—"} size="small" variant="outlined" sx={{ height: 22, fontSize: "0.65rem" }} />
                      </Box>
                      <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.88)", whiteSpace: "pre-wrap" }}>
                        {cl.normalized_text || ""}
                      </Typography>
                      {Array.isArray(cl.evidence) && cl.evidence.length > 0 ? (
                        <Box sx={{ mt: 1 }}>
                          <Typography sx={{ fontSize: "0.7rem", color: "rgba(129,140,248,0.85)", mb: 0.5 }}>
                            {t("readerBody.claimsEvidence")}
                          </Typography>
                          {cl.evidence.map((ev, j) => (
                            <Typography
                              key={`${cl.claim_id}-ev-${j}`}
                              sx={{
                                fontSize: "0.72rem",
                                color: "rgba(255,255,255,0.55)",
                                fontStyle: "italic",
                                mb: 0.5,
                                pl: 0.5,
                                borderLeft: "2px solid rgba(99,102,241,0.35)",
                              }}
                            >
                              {(ev.quote || "").slice(0, 600)}
                              {(ev.quote || "").length > 600 ? "…" : ""}
                            </Typography>
                          ))}
                        </Box>
                      ) : null}
                    </Box>
                  ))}
                </Box>
              )
            ) : null}
          </Collapse>
        </Box>
      ) : null}

      {chunks && !loading && (
        <>
          {traceSummary.length > 0 ? (
            <Box
              sx={{
                mb: 1.5,
                p: 1.25,
                borderRadius: "6px",
                border: "1px solid rgba(99,102,241,0.2)",
                backgroundColor: "rgba(99,102,241,0.08)",
              }}
            >
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)", mb: 0.5 }}>{t("readerBody.focusedContext")}</Typography>
              <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.8)" }}>
                {t("readerBody.openedFrom", { summary: traceSummary.join(" · ") })}
              </Typography>
              <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 1 }}>
                <CursorSmallButton
                  component={Link}
                  to={buildWorkspaceTracePath(workId, "ask", {
                    chunkFingerprint: focusedFingerprint,
                    section: focusedSection,
                    citation,
                  })}
                  sx={{ textDecoration: "none" }}
                >
                  {t("readerBody.returnAsk")}
                </CursorSmallButton>
                <CursorSmallButton
                  component={Link}
                  to={buildWorkspaceTracePath(workId, "evidence", {
                    chunkFingerprint: focusedFingerprint,
                    section: focusedSection,
                    citation,
                  })}
                  sx={{ textDecoration: "none" }}
                >
                  {t("readerBody.openEvidence")}
                </CursorSmallButton>
              </Box>
            </Box>
          ) : null}
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1, mb: 0.5 }}>
            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>
              {t("readerBody.chunksAdvanced", { count: String(chunks.total ?? (chunks.items || []).length) })}
            </Typography>
            <CursorSmallButton type="button" onClick={() => setChunksOpen((o) => !o)} sx={{ fontSize: "0.75rem" }}>
              {chunksOpen ? t("readerBody.hide") : t("readerBody.show")}
            </CursorSmallButton>
          </Box>
          <Collapse in={chunksOpen}>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              {(chunks.items || []).map((ch) => (
                (() => {
                  const fingerprint = String(ch.chunk_fingerprint || "");
                  const sectionPath = String(ch.section_path || "");
                  const highlighted =
                    (focusedFingerprint && fingerprint === focusedFingerprint) ||
                    (focusedSection && sectionPath === focusedSection);
                  return (
                <Box
                  key={`${ch.chunk_fingerprint}-${ch.order}`}
                  sx={{
                    p: 1.5,
                    borderRadius: "6px",
                    border: highlighted ? "1px solid rgba(99,102,241,0.32)" : "1px solid rgba(255,255,255,0.08)",
                    backgroundColor: highlighted ? "rgba(99,102,241,0.08)" : "#141414",
                  }}
                >
                  <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.75 }}>
                    <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}>
                      {t("readerBody.chunkMeta", {
                        section: ch.section_path || "—",
                        fp: String(ch.chunk_fingerprint || ""),
                      })}
                    </Typography>
                    {highlighted ? (
                      <Chip label={t("readerBody.focusedChip")} size="small" sx={{ height: 20, fontSize: "0.6875rem" }} />
                    ) : null}
                  </Box>
                  <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)", mt: 0.5, whiteSpace: "pre-wrap" }}>
                    {(ch.text || "").slice(0, 4000)}
                    {(ch.text || "").length > 4000 ? "…" : ""}
                  </Typography>
                </Box>
                  );
                })()
              ))}
            </Box>
          </Collapse>
        </>
      )}
    </Box>
  );
}
