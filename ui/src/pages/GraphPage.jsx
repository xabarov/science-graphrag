import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";

import { CursorPrimaryButton } from "../components/common/index.js";
import { getWorkGraph } from "../services/researchApi.js";
import { persistWorkId } from "./WorkspacePage/utils/workContext.js";

export default function GraphPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initial = searchParams.get("work_id") || "";
  const [workIdInput, setWorkIdInput] = useState(initial);
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const workId = searchParams.get("work_id") || "";

  useEffect(() => {
    setWorkIdInput(workId);
  }, [workId]);

  useEffect(() => {
    if (workId.trim()) persistWorkId(workId);
  }, [workId]);

  useEffect(() => {
    if (!workId.trim()) {
      setGraph(null);
      setError(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getWorkGraph(workId);
        if (cancelled) return;
        setGraph(res.data);
      } catch (err) {
        if (cancelled) return;
        const msg = err?.response?.data?.detail
          ? JSON.stringify(err.response.data.detail)
          : err?.message || String(err);
        setError(msg);
        setGraph(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workId]);

  function applyWorkId(e) {
    e.preventDefault();
    const next = workIdInput.trim();
    if (next) {
      persistWorkId(next);
      setSearchParams({ work_id: next });
    } else setSearchParams({});
  }

  return (
    <Box sx={{ p: 2, maxWidth: 960 }}>
      <Typography sx={{ fontWeight: 600, mb: 1, color: "rgba(255,255,255,0.9)" }}>Graph</Typography>
      <Typography sx={{ color: "rgba(255,255,255,0.6)", fontSize: "0.8125rem", mb: 2 }}>
        Live: <code style={{ color: "rgba(129,140,248,0.95)" }}>GET /v1/works/{"{work_id}"}/graph</code> (neighborhood JSON).
      </Typography>

      <Box component="form" onSubmit={applyWorkId} sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
        <TextField
          label="work_id"
          value={workIdInput}
          onChange={(ev) => setWorkIdInput(ev.target.value)}
          size="small"
          fullWidth
          sx={{
            maxWidth: 480,
            "& .MuiInputBase-input": { fontSize: "0.8125rem" },
            "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
          }}
        />
        <CursorPrimaryButton type="submit">Load</CursorPrimaryButton>
      </Box>

      {loading && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 2 }}>
          <CircularProgress size={22} sx={{ color: "rgba(129,140,248,0.9)" }} />
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>Loading graph…</Typography>
        </Box>
      )}
      {error && (
        <Alert severity="error" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {error}
        </Alert>
      )}

      {graph && !loading && (
        <Box sx={{ p: 1.5, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#1a1a1a" }}>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 1 }}>
            semantic_available: {String(graph.meta?.semantic_available)} · nodes: {(graph.nodes || []).length} · edges:{" "}
            {(graph.edges || []).length}
          </Typography>
          <Typography
            component="pre"
            sx={{
              m: 0,
              fontSize: "0.75rem",
              color: "rgba(255,255,255,0.75)",
              overflow: "auto",
              maxHeight: 480,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {JSON.stringify(graph, null, 2)}
          </Typography>
        </Box>
      )}
    </Box>
  );
}
