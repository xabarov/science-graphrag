import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import Chip from "@mui/material/Chip";

import { CursorPrimaryButton, CursorSmallButton } from "../components/common/index.js";
import PageHeader from "../components/layout/PageHeader.jsx";
import { getWorks } from "../services/researchApi.js";
import { buildWorkspacePath, persistWorkId } from "./WorkspacePage/utils/workContext.js";
import { getContinueWorkspaceTarget, getRecentWorks, rememberRecentWork } from "./HomePage/homeState.js";

export default function CorpusPage() {
  const [q, setQ] = useState("");
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [recentWorks, setRecentWorks] = useState([]);
  const [continueTarget, setContinueTarget] = useState(null);

  useEffect(() => {
    setRecentWorks(getRecentWorks().slice(0, 4));
    setContinueTarget(getContinueWorkspaceTarget());
  }, []);

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

  function onOpenWorkspace(workId) {
    persistWorkId(workId);
    const item = items.find((candidate) => candidate.work_id === workId);
    rememberRecentWork({
      workId,
      title: item?.title || "",
      year: item?.year ?? null,
      tab: "overview",
    });
  }

  return (
    <Box sx={{ p: 2, maxWidth: 960 }}>
      <PageHeader
        eyebrow="Corpus browser"
        title="Corpus"
        description={
          <>
            Browse indexed works (<code style={{ color: "rgba(129,140,248,0.95)" }}>GET /v1/works</code>). Open a work in the <strong>Workspace</strong>{" "}
            to read, ask questions, and inspect evidence in one place.
          </>
        }
        actions={
          <>
            <CursorSmallButton component={Link} to="/" sx={{ textDecoration: "none" }}>
              Home
            </CursorSmallButton>
            {continueTarget ? (
              <CursorSmallButton component={Link} to={continueTarget.path} sx={{ textDecoration: "none" }}>
                Continue workspace
              </CursorSmallButton>
            ) : null}
          </>
        }
      />

      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 1.5, mb: 2.5 }}>
        <Box
          sx={{
            p: 1.75,
            borderRadius: "6px",
            border: "1px solid rgba(99,102,241,0.24)",
            backgroundColor: "rgba(99,102,241,0.08)",
          }}
        >
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)", mb: 0.75 }}>Continue flow</Typography>
          <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: "rgba(255,255,255,0.9)" }}>
            {continueTarget ? "Resume last workspace" : "Start from the corpus"}
          </Typography>
          <Typography sx={{ mt: 0.9, fontSize: "0.8125rem", color: "rgba(255,255,255,0.62)", lineHeight: 1.55 }}>
            {continueTarget
              ? "Jump back into the last active work context or pick a different paper below."
              : "There is no saved workspace yet. Use the corpus to select a paper and begin a new research session."}
          </Typography>
          <Box sx={{ mt: 1.5, display: "flex", flexWrap: "wrap", gap: 1 }}>
            {continueTarget ? (
              <CursorPrimaryButton component={Link} to={continueTarget.path} sx={{ textDecoration: "none" }}>
                Continue workspace
              </CursorPrimaryButton>
            ) : null}
            <CursorSmallButton component={Link} to="/" sx={{ textDecoration: "none" }}>
              Open home
            </CursorSmallButton>
          </Box>
        </Box>

        <Box
          sx={{
            p: 1.75,
            borderRadius: "6px",
            border: "1px solid rgba(255,255,255,0.08)",
            backgroundColor: "#1a1a1a",
          }}
        >
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mb: 0.75 }}>Recent works</Typography>
          {recentWorks.length === 0 ? (
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>
              No recent works yet. Open a paper in Workspace to build a quicker continue flow.
            </Typography>
          ) : (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.9 }}>
              {recentWorks.map((item) => (
                <Box key={item.workId} sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1 }}>
                  <Box sx={{ minWidth: 0 }}>
                    <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)", fontWeight: 600 }}>
                      {item.title || item.workId}
                    </Typography>
                    <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.25 }}>{item.workId}</Typography>
                  </Box>
                  <CursorSmallButton component={Link} to={buildWorkspacePath(item.workId, item.tab || "overview")} sx={{ textDecoration: "none" }}>
                    Open
                  </CursorSmallButton>
                </Box>
              ))}
            </Box>
          )}
        </Box>
      </Box>

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
        <CursorPrimaryButton
          type="button"
          disabled={loading}
          onClick={() => {
            setQ("");
            load("");
          }}
        >
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
              p: 1.75,
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
            </Typography>
            <Box sx={{ mt: 0.9, display: "flex", flexWrap: "wrap", gap: 0.75 }}>
              {w.year != null ? <Chip label={`Year ${w.year}`} size="small" sx={{ height: 22, fontSize: "0.6875rem" }} /> : null}
              {w.has_semantic_layer ? <Chip label="Semantic ready" size="small" sx={{ height: 22, fontSize: "0.6875rem" }} /> : null}
              <Chip label="Workspace-first" size="small" sx={{ height: 22, fontSize: "0.6875rem" }} />
            </Box>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mt: 1.25, alignItems: "center" }}>
              <CursorPrimaryButton
                component={Link}
                to={buildWorkspacePath(w.work_id, "overview")}
                onClick={() => onOpenWorkspace(w.work_id)}
                sx={{ textDecoration: "none", fontSize: "0.8125rem" }}
              >
                Open workspace
              </CursorPrimaryButton>
              <CursorSmallButton
                component={Link}
                to={buildWorkspacePath(w.work_id, "reader")}
                onClick={() => onOpenWorkspace(w.work_id)}
                sx={{ textDecoration: "none" }}
              >
                Reader
              </CursorSmallButton>
              <CursorSmallButton
                component={Link}
                to={buildWorkspacePath(w.work_id, "ask")}
                onClick={() => onOpenWorkspace(w.work_id)}
                sx={{ textDecoration: "none" }}
              >
                Ask
              </CursorSmallButton>
              <CursorSmallButton
                component={Link}
                to={buildWorkspacePath(w.work_id, "evidence")}
                onClick={() => onOpenWorkspace(w.work_id)}
                sx={{ textDecoration: "none" }}
              >
                Evidence
              </CursorSmallButton>
              <CursorSmallButton component={Link} to={`/graph?work_id=${encodeURIComponent(w.work_id)}`} sx={{ textDecoration: "none" }}>
                Graph
              </CursorSmallButton>
            </Box>
          </Box>
        ))}
      </Box>

      {!loading && !error && items.length === 0 && (
        <Box
          sx={{
            mt: 2,
            p: 2,
            borderRadius: "6px",
            border: "1px dashed rgba(255,255,255,0.12)",
            backgroundColor: "rgba(255,255,255,0.02)",
          }}
        >
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)" }}>
            {q.trim() ? "No matching works" : "No works in corpus"}
          </Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)", mt: 0.75 }}>
            {q.trim()
              ? "Try a broader title, DOI, or arXiv query, or reset the search to browse the full corpus."
              : "Ingest a corpus via the API or pipeline, then refresh this page. Works will appear here with a clear path into Workspace."}
          </Typography>
        </Box>
      )}
    </Box>
  );
}
