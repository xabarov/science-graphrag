import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";

import { CursorPrimaryButton } from "../components/common/index.js";
import { getWorks } from "../services/researchApi.js";

export default function WorkspacePage() {
  const [q, setQ] = useState("");
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async (search) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getWorks({ q: search || undefined, limit: 50, offset: 0 });
      setItems(Array.isArray(res.data?.items) ? res.data.items : []);
      setTotal(Number.isFinite(Number(res.data?.total)) ? Number(res.data.total) : 0);
    } catch (err) {
      const msg = err?.response?.data?.detail
        ? JSON.stringify(err.response.data.detail)
        : err?.message || String(err);
      setError(msg);
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load("");
  }, [load]);

  function onSearch(e) {
    e.preventDefault();
    load(q);
  }

  return (
    <Box sx={{ p: 2, maxWidth: 960 }}>
      <Typography sx={{ fontWeight: 600, mb: 1, color: "rgba(255,255,255,0.9)" }}>Workspace</Typography>
      <Typography sx={{ color: "rgba(255,255,255,0.6)", fontSize: "0.8125rem", mb: 2 }}>
        Live list: <code style={{ color: "rgba(129,140,248,0.95)" }}>GET /v1/works</code>. Use Ask / Reader / Graph with a selected{" "}
        <code style={{ color: "rgba(129,140,248,0.95)" }}>work_id</code>.
      </Typography>

      <Box component="form" onSubmit={onSearch} sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2, alignItems: "flex-start" }}>
        <TextField
          label="Search (title / doi / arxiv)"
          value={q}
          onChange={(ev) => setQ(ev.target.value)}
          size="small"
          sx={{
            minWidth: 240,
            "& .MuiInputBase-input": { fontSize: "0.8125rem" },
            "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
          }}
        />
        <CursorPrimaryButton type="submit" disabled={loading}>
          Search
        </CursorPrimaryButton>
        <CursorPrimaryButton type="button" disabled={loading} onClick={() => { setQ(""); load(""); }}>
          Reset
        </CursorPrimaryButton>
      </Box>

      {loading && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 2 }}>
          <CircularProgress size={22} sx={{ color: "rgba(129,140,248,0.9)" }} />
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>Loading works…</Typography>
        </Box>
      )}
      {error && (
        <Alert severity="error" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {error}
        </Alert>
      )}

      {!loading && !error && (
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 1 }}>
          Total: {total}
        </Typography>
      )}

      <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
        {items.map((w) => (
          <Box
            key={w.work_id}
            sx={{
              p: 1.5,
              borderRadius: "6px",
              border: "1px solid rgba(255,255,255,0.08)",
              backgroundColor: "#1a1a1a",
            }}
          >
            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.9)" }}>
              {w.title || "(no title)"}
            </Typography>
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mt: 0.5 }}>
              {w.year != null ? `${w.year} · ` : ""}
              {w.work_id}
              {w.has_semantic_layer ? " · semantic" : ""}
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mt: 1 }}>
              <Link
                to={`/reader?work_id=${encodeURIComponent(w.work_id)}`}
                style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}
              >
                Reader
              </Link>
              <Link
                to={`/graph?work_id=${encodeURIComponent(w.work_id)}`}
                style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}
              >
                Graph
              </Link>
              <Link
                to={`/evidence?work_id=${encodeURIComponent(w.work_id)}`}
                style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}
              >
                Evidence
              </Link>
              <Link to="/ask" style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}>
                Ask
              </Link>
            </Box>
          </Box>
        ))}
      </Box>

      {!loading && !error && items.length === 0 && (
        <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>No works yet — ingest a corpus, then refresh.</Typography>
      )}
    </Box>
  );
}
