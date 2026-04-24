import React, { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import Chip from "@mui/material/Chip";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import { Link } from "react-router-dom";

import { formatResearchApiError, getWorkClaims, getWorkChunks } from "../../services/researchApi.js";
import { CursorSmallButton } from "../common/index.js";
import { buildWorkspaceTracePath, describeTraceabilityState } from "./traceabilityState.js";
import { useI18n } from "../../i18n/I18nContext.jsx";

/**
 * Evidence (chunk fingerprints) for a fixed work_id.
 * @param {{ workId: string, highlightedFingerprint?: string, highlightedSection?: string, citation?: string }} props
 */
export default function EvidenceWorkBody({
  workId,
  highlightedFingerprint = "",
  highlightedSection = "",
  citation = "",
}) {
  const { t } = useI18n();
  const [chunks, setChunks] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [onlyClaimEvidence, setOnlyClaimEvidence] = useState(false);
  const [claimChunkFingerprints, setClaimChunkFingerprints] = useState(() => new Set());
  const traceSummary = describeTraceabilityState({
    chunkFingerprint: highlightedFingerprint,
    section: highlightedSection,
    citation,
  });

  useEffect(() => {
    if (!workId.trim()) {
      setChunks(null);
      setError(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [cRes, clRes] = await Promise.all([
          getWorkChunks(workId, { limit: 200, offset: 0 }),
          getWorkClaims(workId).catch(() => ({ data: { items: [] } })),
        ]);
        if (cancelled) return;
        setChunks(cRes.data);
        const fps = new Set();
        const items = clRes.data?.items;
        if (Array.isArray(items)) {
          for (const cl of items) {
            for (const ev of cl.evidence || []) {
              const fp = String(ev.chunk_fingerprint || "").trim();
              if (fp) fps.add(fp);
            }
          }
        }
        setClaimChunkFingerprints(fps);
      } catch (err) {
        if (cancelled) return;
        setError(formatResearchApiError(err));
        setChunks(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workId]);

  const visibleChunkItems = useMemo(() => {
    const raw = chunks?.items;
    if (!Array.isArray(raw)) return [];
    if (!onlyClaimEvidence || claimChunkFingerprints.size === 0) return raw;
    return raw.filter((ch) => claimChunkFingerprints.has(String(ch.chunk_fingerprint || "").trim()));
  }, [chunks, onlyClaimEvidence, claimChunkFingerprints]);

  return (
    <Box>
      {loading && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 2 }}>
          <CircularProgress size={22} sx={{ color: "rgba(129,140,248,0.9)" }} />
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("evidenceBody.loading")}</Typography>
        </Box>
      )}
      {error && (
        <Alert severity="error" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {error}
        </Alert>
      )}

      {chunks && !loading && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
          {traceSummary.length > 0 ? (
            <Box
              sx={{
                p: 1.25,
                borderRadius: "6px",
                border: "1px solid rgba(99,102,241,0.2)",
                backgroundColor: "rgba(99,102,241,0.08)",
              }}
            >
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)", mb: 0.5 }}>{t("evidenceBody.traceTitle")}</Typography>
              <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.8)" }}>
                {t("evidenceBody.focus", { summary: traceSummary.join(" · ") })}
              </Typography>
            </Box>
          ) : null}
          <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 1 }}>
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>
              {t("evidenceBody.total", { total: String(chunks.total ?? "—") })}
            </Typography>
            {claimChunkFingerprints.size > 0 ? (
              <FormControlLabel
                control={
                  <Switch
                    size="small"
                    checked={onlyClaimEvidence}
                    onChange={(_e, v) => setOnlyClaimEvidence(v)}
                    sx={{ ml: 0.5 }}
                  />
                }
                label={<Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.65)" }}>{t("evidenceBody.filterClaimsOnly")}</Typography>}
              />
            ) : null}
          </Box>
          {visibleChunkItems.map((ch) => (
            (() => {
              const fingerprint = String(ch.chunk_fingerprint || "");
              const sectionPath = String(ch.section_path || "");
              const highlighted =
                (highlightedFingerprint && fingerprint === highlightedFingerprint) ||
                (highlightedSection && sectionPath === highlightedSection);
              return (
            <Box
              key={`${ch.chunk_fingerprint}-${ch.order}`}
              sx={{
                py: 0.9,
                px: 0.75,
                borderRadius: "6px",
                border: highlighted ? "1px solid rgba(99,102,241,0.32)" : "1px solid transparent",
                backgroundColor: highlighted ? "rgba(99,102,241,0.08)" : "transparent",
                borderBottom: highlighted ? "1px solid rgba(99,102,241,0.32)" : "1px solid rgba(255,255,255,0.06)",
              }}
            >
              <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.75 }}>
                <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.9)", fontFamily: "monospace" }}>
                  {ch.chunk_fingerprint}
                </Typography>
                {highlighted ? (
                  <Chip label={t("evidenceBody.answerLinked")} size="small" sx={{ height: 20, fontSize: "0.6875rem" }} />
                ) : null}
              </Box>
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.25 }}>{ch.section_path || "—"}</Typography>
              <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)", mt: 0.35 }}>
                {(ch.text || "").slice(0, 600)}
                {(ch.text || "").length > 600 ? "…" : ""}
              </Typography>
              <Box sx={{ mt: 0.75, display: "flex", flexWrap: "wrap", gap: 1 }}>
                <CursorSmallButton
                  component={Link}
                  to={buildWorkspaceTracePath(workId, "reader", {
                    chunkFingerprint: fingerprint,
                    section: sectionPath,
                    citation,
                  })}
                  sx={{ textDecoration: "none" }}
                >
                  {t("evidenceBody.openReader")}
                </CursorSmallButton>
                <CursorSmallButton
                  component={Link}
                  to={buildWorkspaceTracePath(workId, "graph", {
                    section: sectionPath,
                    citation,
                  })}
                  sx={{ textDecoration: "none" }}
                >
                  {t("evidenceBody.openGraph")}
                </CursorSmallButton>
                <CursorSmallButton
                  component={Link}
                  to={buildWorkspaceTracePath(workId, "ask", {
                    chunkFingerprint: fingerprint,
                    section: sectionPath,
                    citation,
                  })}
                  sx={{ textDecoration: "none" }}
                >
                  {t("evidenceBody.continueAsk")}
                </CursorSmallButton>
              </Box>
            </Box>
              );
            })()
          ))}
        </Box>
      )}
    </Box>
  );
}
