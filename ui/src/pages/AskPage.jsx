import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Alert from "@mui/material/Alert";
import Chip from "@mui/material/Chip";

import { CursorPrimaryButton } from "../components/common/index.js";
import { buildQueryBody, normalizeQueryResponse, postQuery } from "../services/researchApi.js";

function FlagChips({ label, items }) {
  if (!items || items.length === 0) return null;
  return (
    <Box sx={{ mt: 1 }}>
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 0.5 }}>{label}</Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
        {items.map((d) => (
          <Chip key={d} label={d} size="small" sx={{ height: 22, fontSize: "0.75rem" }} />
        ))}
      </Box>
    </Box>
  );
}

export default function AskPage() {
  const [query, setQuery] = useState("object detection benchmarks");
  const [workId, setWorkId] = useState("");
  const [topK, setTopK] = useState("5");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [normalized, setNormalized] = useState(null);

  const bodyPreview = useMemo(() => buildQueryBody(query, workId, topK), [query, workId, topK]);

  async function onSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setNormalized(null);
    try {
      const res = await postQuery(bodyPreview);
      setNormalized(normalizeQueryResponse(res.data));
    } catch (err) {
      const msg = err?.response?.data?.detail
        ? JSON.stringify(err.response.data.detail)
        : err?.message || String(err);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box sx={{ p: 2, maxWidth: 960 }}>
      <Typography sx={{ fontWeight: 600, mb: 1, color: "rgba(255,255,255,0.9)" }}>Ask</Typography>
      <Typography sx={{ color: "rgba(255,255,255,0.6)", fontSize: "0.8125rem", mb: 2 }}>
        POST /v1/query (live). Set <code style={{ color: "rgba(129,140,248,0.95)" }}>VITE_API_BASE_URL</code> if the API is not same-origin.
      </Typography>

      <Box component="form" onSubmit={onSubmit} sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
        <TextField
          label="Query"
          value={query}
          onChange={(ev) => setQuery(ev.target.value)}
          multiline
          minRows={2}
          fullWidth
          size="small"
          sx={{
            "& .MuiInputBase-input": { fontSize: "0.8125rem" },
            "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
          }}
        />
        <TextField
          label="work_id (optional)"
          value={workId}
          onChange={(ev) => setWorkId(ev.target.value)}
          fullWidth
          size="small"
          sx={{
            "& .MuiInputBase-input": { fontSize: "0.8125rem" },
            "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
          }}
        />
        <TextField
          label="top_k"
          value={topK}
          onChange={(ev) => setTopK(ev.target.value)}
          fullWidth
          size="small"
          sx={{
            "& .MuiInputBase-input": { fontSize: "0.8125rem" },
            "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
          }}
        />
        <Box>
          <CursorPrimaryButton type="submit" disabled={loading}>
            {loading ? "Querying…" : "Run query"}
          </CursorPrimaryButton>
        </Box>
      </Box>

      {error ? (
        <Alert severity="error" sx={{ mt: 2, fontSize: "0.8125rem" }}>
          {error}
        </Alert>
      ) : null}

      {normalized ? (
        <Box
          sx={{
            mt: 2,
            p: 2,
            borderRadius: "6px",
            border: "1px solid rgba(255,255,255,0.08)",
            backgroundColor: "#1a1a1a",
          }}
        >
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 1 }}>Answer</Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)", whiteSpace: "pre-wrap" }}>
            {normalized.answer || "—"}
          </Typography>

          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.5 }}>Citations</Typography>
          {normalized.citations.length === 0 ? (
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>None</Typography>
          ) : (
            normalized.citations.map((c, i) => (
              <Box key={i} sx={{ mb: 1, fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)" }}>
                #{c.rank} score={String(c.score)} work_id={String(c.work_id ?? "—")} fp=
                {String(c.chunk_fingerprint ?? "—")}
                {c.work_id ? (
                  <Box sx={{ mt: 0.5, display: "flex", flexWrap: "wrap", gap: 1 }}>
                    <Link
                      to={`/reader?work_id=${encodeURIComponent(String(c.work_id))}`}
                      style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}
                    >
                      Reader
                    </Link>
                    <Link
                      to={`/evidence?work_id=${encodeURIComponent(String(c.work_id))}`}
                      style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}
                    >
                      Evidence
                    </Link>
                  </Box>
                ) : null}
                <Box component="span" sx={{ display: "block", color: "rgba(255,255,255,0.55)", mt: 0.25 }}>
                  {String(c.excerpt ?? "").slice(0, 280)}
                  {String(c.excerpt ?? "").length > 280 ? "…" : ""}
                </Box>
              </Box>
            ))
          )}

          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.5 }}>Graph context</Typography>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)" }}>
            semantic_available={String(normalized.graph_context.semantic_available)} context_work_id=
            {normalized.graph_context.context_work_id ?? "null"}
            {normalized.graph_context.error ? ` error=${normalized.graph_context.error}` : ""}
          </Typography>
          <FlagChips label="graph_context.degraded" items={normalized.graph_context.degraded} />
          <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 0.5 }}>
            {normalized.graph_context.methods.map((m) => (
              <Chip key={`m-${m}`} label={m} size="small" sx={{ height: 22, fontSize: "0.75rem" }} />
            ))}
            {normalized.graph_context.datasets.map((d) => (
              <Chip key={`d-${d}`} label={d} size="small" sx={{ height: 22, fontSize: "0.75rem" }} />
            ))}
          </Box>

          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.5 }}>Retrieval trace</Typography>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)", whiteSpace: "pre-wrap" }}>
            {JSON.stringify(
              {
                qdrant_collection: normalized.retrieval_trace.qdrant_collection,
                top_k_requested: normalized.retrieval_trace.top_k_requested,
                citations_returned: normalized.retrieval_trace.citations_returned,
                hit_count: normalized.retrieval_trace.hit_count,
                filter_work_id: normalized.retrieval_trace.filter_work_id,
                resolved_work_id: normalized.retrieval_trace.resolved_work_id,
                embedding: normalized.retrieval_trace.embedding,
                degraded: normalized.retrieval_trace.degraded,
              },
              null,
              2,
            )}
          </Typography>
        </Box>
      ) : null}
    </Box>
  );
}
