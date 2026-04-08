import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";

import { CursorPrimaryButton, CursorSmallButton } from "../components/common/index.js";
import PageHeader from "../components/layout/PageHeader.jsx";
import WorkIdGlossaryHint from "../components/layout/WorkIdGlossaryHint.jsx";
import { mainShellContentSx } from "../components/layout/mainShellContentSx.js";
import { getWorks } from "../services/researchApi.js";
import { buildWorkspacePath, persistWorkId } from "./WorkspacePage/utils/workContext.js";
import { rememberRecentWork } from "./HomePage/homeState.js";
import { useCorpusEntryState } from "./HomePage/useCorpusEntryState.js";

const PAGE_SIZE = 40;

export default function CorpusPage() {
  const [q, setQ] = useState("");
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [sortBy, setSortBy] = useState("api");
  const [viewDensity, setViewDensity] = useState("cards");
  const [semanticFilter, setSemanticFilter] = useState("all");
  const [yearMin, setYearMin] = useState("");
  const [yearMax, setYearMax] = useState("");

  const { recentWorks, continueTarget, refreshCorpusEntryState } = useCorpusEntryState({ recentLimit: 4 });

  useEffect(() => {
    refreshCorpusEntryState();
  }, [refreshCorpusEntryState]);

  const loadFirst = useCallback(async (search) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getWorks({ q: search || undefined, limit: PAGE_SIZE, offset: 0 });
      const chunk = Array.isArray(res.data?.items) ? res.data.items : [];
      const tot = Number.isFinite(Number(res.data?.total)) ? Number(res.data.total) : 0;
      setItems(chunk);
      setTotal(tot);
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

  const loadMore = useCallback(async () => {
    if (loadingMore || items.length >= total) return;
    setLoadingMore(true);
    setError(null);
    try {
      const res = await getWorks({ q: q.trim() || undefined, limit: PAGE_SIZE, offset: items.length });
      const chunk = Array.isArray(res.data?.items) ? res.data.items : [];
      setItems((prev) => [...prev, ...chunk]);
    } catch (err) {
      const msg = err?.response?.data?.detail
        ? JSON.stringify(err.response.data.detail)
        : err?.message || String(err);
      setError(msg);
    } finally {
      setLoadingMore(false);
    }
  }, [items.length, loadingMore, q, total]);

  useEffect(() => {
    loadFirst("");
  }, [loadFirst]);

  function onSearch(e) {
    e.preventDefault();
    loadFirst(q.trim() || undefined);
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
    refreshCorpusEntryState();
  }

  const filteredItems = useMemo(() => {
    return items.filter((w) => {
      if (semanticFilter === "ready" && !w.has_semantic_layer) return false;
      if (semanticFilter === "not_ready" && w.has_semantic_layer) return false;
      const y = Number(w.year);
      const minY = yearMin.trim() === "" ? null : Number(yearMin);
      const maxY = yearMax.trim() === "" ? null : Number(yearMax);
      if (minY != null && Number.isFinite(minY) && (!Number.isFinite(y) || y < minY)) return false;
      if (maxY != null && Number.isFinite(maxY) && (!Number.isFinite(y) || y > maxY)) return false;
      return true;
    });
  }, [items, semanticFilter, yearMin, yearMax]);

  const sortedItems = useMemo(() => {
    const arr = [...filteredItems];
    if (sortBy === "title") {
      arr.sort((a, b) => String(a.title || "").localeCompare(String(b.title || ""), undefined, { sensitivity: "base" }));
    } else if (sortBy === "year_desc") {
      arr.sort((a, b) => (Number(b.year) || 0) - (Number(a.year) || 0));
    }
    return arr;
  }, [filteredItems, sortBy]);

  const canLoadMore = !loading && items.length < total;

  function renderWorkRow(w) {
    if (viewDensity === "compact") {
      return (
        <Box
          key={w.work_id}
          sx={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            gap: 1,
            py: 1,
            px: 1.25,
            borderRadius: "6px",
            border: "1px solid rgba(255,255,255,0.08)",
            backgroundColor: "#1a1a1a",
          }}
        >
          <Box sx={{ flex: "1 1 200px", minWidth: 0 }}>
            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.9)" }} noWrap>
              {w.title || "(no title)"}
            </Typography>
            <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.45)" }} noWrap>
              {w.year != null ? `${w.year} · ` : ""}
              {w.work_id}
            </Typography>
          </Box>
          <CursorPrimaryButton
            component={Link}
            to={buildWorkspacePath(w.work_id, "overview")}
            onClick={() => onOpenWorkspace(w.work_id)}
            sx={{ textDecoration: "none", fontSize: "0.75rem", minHeight: 28 }}
          >
            Workspace
          </CursorPrimaryButton>
        </Box>
      );
    }
    return (
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
    );
  }

  return (
    <Box sx={{ p: { xs: 1.5, sm: 2 }, ...mainShellContentSx }}>
      <PageHeader
        eyebrow="Corpus browser"
        title="Corpus"
        description={<WorkIdGlossaryHint variant="corpus" />}
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

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "repeat(auto-fit, minmax(260px, 1fr))" },
          gap: 1.5,
          mb: 2.5,
        }}
      >
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
            minWidth: { xs: "100%", sm: 240 },
            flex: { xs: "1 1 100%", sm: "0 1 auto" },
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
            loadFirst(undefined);
          }}
        >
          Reset
        </CursorPrimaryButton>
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel id="corpus-sort">Sort</InputLabel>
          <Select labelId="corpus-sort" label="Sort" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <MenuItem value="api">API order</MenuItem>
            <MenuItem value="title">Title (A–Z)</MenuItem>
            <MenuItem value="year_desc">Year (newest)</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel id="corpus-view">View</InputLabel>
          <Select labelId="corpus-view" label="View" value={viewDensity} onChange={(e) => setViewDensity(e.target.value)}>
            <MenuItem value="cards">Cards</MenuItem>
            <MenuItem value="compact">Compact</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel id="corpus-sem">Semantic</InputLabel>
          <Select labelId="corpus-sem" label="Semantic" value={semanticFilter} onChange={(e) => setSemanticFilter(e.target.value)}>
            <MenuItem value="all">All works</MenuItem>
            <MenuItem value="ready">Semantic ready</MenuItem>
            <MenuItem value="not_ready">Not semantic-ready</MenuItem>
          </Select>
        </FormControl>
        <TextField
          label="Year min"
          value={yearMin}
          onChange={(e) => setYearMin(e.target.value)}
          size="small"
          type="number"
          sx={{ width: 100, "& .MuiInputBase-input": { fontSize: "0.8125rem" } }}
        />
        <TextField
          label="Year max"
          value={yearMax}
          onChange={(e) => setYearMax(e.target.value)}
          size="small"
          type="number"
          sx={{ width: 100, "& .MuiInputBase-input": { fontSize: "0.8125rem" } }}
        />
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
          Total in corpus: {total}
          {items.length < total ? ` · Loaded: ${items.length}` : null}
          {filteredItems.length !== items.length ? ` · After filters: ${filteredItems.length}` : null}
        </Typography>
      )}

      <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>{sortedItems.map(renderWorkRow)}</Box>

      {!loading && !error && canLoadMore ? (
        <Box sx={{ mt: 2, display: "flex", alignItems: "center", gap: 1 }}>
          <CursorPrimaryButton type="button" disabled={loadingMore} onClick={() => loadMore().catch(() => {})}>
            {loadingMore ? "Loading…" : "Load more"}
          </CursorPrimaryButton>
        </Box>
      ) : null}

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

      {!loading && !error && items.length > 0 && sortedItems.length === 0 ? (
        <Alert severity="info" sx={{ mt: 2, fontSize: "0.8125rem" }}>
          No works match the current filters. Adjust semantic or year filters, or load more pages from the API.
        </Alert>
      ) : null}
    </Box>
  );
}
