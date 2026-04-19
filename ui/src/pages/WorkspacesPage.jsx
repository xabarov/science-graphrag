import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import Chip from "@mui/material/Chip";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";

import { CursorPrimaryButton, CursorSmallButton } from "../components/common/index.js";
import PageHeader from "../components/layout/PageHeader.jsx";
import WorkIdGlossaryHint from "../components/layout/WorkIdGlossaryHint.jsx";
import { mainShellContentSx } from "../components/layout/mainShellContentSx.js";
import { formatResearchApiError, getWorks } from "../services/researchApi.js";
import { buildWorkspacePath, persistWorkId } from "./WorkspacePage/utils/workContext.js";
import { rememberRecentWork } from "./HomePage/homeState.js";
import { useCorpusEntryState } from "./HomePage/useCorpusEntryState.js";
import {
  addWorkToWorkspace,
  createWorkspace,
  deleteWorkspaceApi,
  getActiveWorkspaceId,
  listWorkspaces,
  mergeWorkspacesApi,
  renameWorkspace,
  setActiveWorkspaceId,
} from "../utils/workspaceStore.js";

const PAGE_SIZE = 40;

function workspacePaperUrl(workspaceId, workId) {
  const p = new URLSearchParams();
  if (workspaceId) p.set("workspace_id", workspaceId);
  if (workId) p.set("work_id", workId);
  return `/workspace?${p.toString()}`;
}

export default function WorkspacesPage() {
  const [q, setQ] = useState("");
  const [lastSearch, setLastSearch] = useState("");
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

  const [workspaces, setWorkspaces] = useState([]);
  const [wsLoading, setWsLoading] = useState(true);
  const [wsError, setWsError] = useState(null);
  const [newWsName, setNewWsName] = useState("Research");
  const [targetWorkspaceId, setTargetWorkspaceId] = useState("");
  const [mergeKeep, setMergeKeep] = useState("");
  const [mergeDrop, setMergeDrop] = useState("");
  const [mergeBusy, setMergeBusy] = useState(false);

  const { recentWorks, continueTarget, refreshCorpusEntryState } = useCorpusEntryState({ recentLimit: 4 });

  const loadWorkspaces = useCallback(async () => {
    setWsLoading(true);
    setWsError(null);
    try {
      const list = await listWorkspaces();
      setWorkspaces(list);
      const active = getActiveWorkspaceId();
      const pick = active && list.some((x) => x.id === active) ? active : list[0]?.id || "";
      setTargetWorkspaceId(pick);
      if (pick) setActiveWorkspaceId(pick);
    } catch (e) {
      setWsError(formatResearchApiError(e));
      setWorkspaces([]);
    } finally {
      setWsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshCorpusEntryState();
    loadWorkspaces();
  }, [refreshCorpusEntryState, loadWorkspaces]);

  const worksServerParams = useCallback(() => {
    const ymin = yearMin.trim() === "" ? undefined : Number(yearMin);
    const ymax = yearMax.trim() === "" ? undefined : Number(yearMax);
    let hasSemantic;
    if (semanticFilter === "ready") hasSemantic = true;
    else if (semanticFilter === "not_ready") hasSemantic = false;
    return {
      yearMin: Number.isFinite(ymin) ? ymin : undefined,
      yearMax: Number.isFinite(ymax) ? ymax : undefined,
      hasSemantic,
    };
  }, [yearMin, yearMax, semanticFilter]);

  const loadFirst = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getWorks({
        q: lastSearch.trim() || undefined,
        limit: PAGE_SIZE,
        offset: 0,
        ...worksServerParams(),
      });
      const chunk = Array.isArray(res.data?.items) ? res.data.items : [];
      const tot = Number.isFinite(Number(res.data?.total)) ? Number(res.data.total) : 0;
      setItems(chunk);
      setTotal(tot);
    } catch (err) {
      setError(formatResearchApiError(err));
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [lastSearch, worksServerParams]);

  const loadMore = useCallback(async () => {
    if (loadingMore || items.length >= total) return;
    setLoadingMore(true);
    setError(null);
    try {
      const res = await getWorks({
        q: lastSearch.trim() || undefined,
        limit: PAGE_SIZE,
        offset: items.length,
        ...worksServerParams(),
      });
      const chunk = Array.isArray(res.data?.items) ? res.data.items : [];
      setItems((prev) => [...prev, ...chunk]);
    } catch (err) {
      setError(formatResearchApiError(err));
    } finally {
      setLoadingMore(false);
    }
  }, [items.length, lastSearch, loadingMore, total, worksServerParams]);

  useEffect(() => {
    loadFirst();
  }, [loadFirst]);

  function onSearch(e) {
    e.preventDefault();
    setLastSearch(q.trim());
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

  async function handleCreateWorkspace() {
    setWsError(null);
    try {
      const row = await createWorkspace(newWsName.trim() || "Workspace");
      await loadWorkspaces();
      if (row?.id) {
        setTargetWorkspaceId(row.id);
        setActiveWorkspaceId(row.id);
      }
    } catch (e) {
      setWsError(formatResearchApiError(e));
    }
  }

  async function handleDeleteWorkspace(id) {
    if (!window.confirm("Delete this workspace?")) return;
    setWsError(null);
    try {
      await deleteWorkspaceApi(id);
      await loadWorkspaces();
    } catch (e) {
      setWsError(formatResearchApiError(e));
    }
  }

  async function handleRenameWorkspace(id, name) {
    setWsError(null);
    try {
      await renameWorkspace(id, name);
      await loadWorkspaces();
    } catch (e) {
      setWsError(formatResearchApiError(e));
    }
  }

  async function handleAddPaperToTarget(workId) {
    const tw = targetWorkspaceId;
    if (!tw) {
      setWsError("Select or create a target workspace first.");
      return;
    }
    setWsError(null);
    try {
      await addWorkToWorkspace(tw, workId);
      await loadWorkspaces();
    } catch (e) {
      setWsError(formatResearchApiError(e));
    }
  }

  async function handleMergeWorkspaces() {
    if (!mergeKeep.trim() || !mergeDrop.trim()) return;
    setMergeBusy(true);
    setWsError(null);
    try {
      await mergeWorkspacesApi(mergeKeep.trim(), mergeDrop.trim());
      setMergeKeep("");
      setMergeDrop("");
      await loadWorkspaces();
    } catch (e) {
      setWsError(formatResearchApiError(e));
    } finally {
      setMergeBusy(false);
    }
  }

  function exportWorkspacesJson() {
    const blob = new Blob([JSON.stringify({ workspaces, exportedAt: new Date().toISOString() }, null, 2)], {
      type: "application/json",
    });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "science-graphrag-workspaces.json";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function onImportWorkspaces(ev) {
    const f = ev.target.files?.[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result || "{}"));
        const arr = Array.isArray(parsed?.workspaces) ? parsed.workspaces : [];
        setWsError(arr.length ? `Imported snapshot lists ${arr.length} workspace(s) (read-only preview).` : "No workspaces in file.");
      } catch {
        setWsError("Invalid JSON file.");
      }
    };
    reader.readAsText(f);
    ev.target.value = "";
  }

  const sortedItems = useMemo(() => {
    const arr = [...items];
    if (sortBy === "title") {
      arr.sort((a, b) => String(a.title || "").localeCompare(String(b.title || ""), undefined, { sensitivity: "base" }));
    } else if (sortBy === "year_desc") {
      arr.sort((a, b) => (Number(b.year) || 0) - (Number(a.year) || 0));
    }
    return arr;
  }, [items, sortBy]);

  const canLoadMore = !loading && items.length < total;
  const tw = targetWorkspaceId;

  function renderWorkRow(w) {
    const wsUrl = tw ? workspacePaperUrl(tw, w.work_id) : buildWorkspacePath(w.work_id);
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
          <CursorPrimaryButton component={Link} to={wsUrl} onClick={() => onOpenWorkspace(w.work_id)} sx={{ textDecoration: "none", fontSize: "0.75rem", minHeight: 28 }}>
            Workspace
          </CursorPrimaryButton>
          <CursorSmallButton type="button" onClick={() => handleAddPaperToTarget(w.work_id)} disabled={!tw}>
            Add to target
          </CursorSmallButton>
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
        </Box>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mt: 1.25, alignItems: "center" }}>
          <CursorPrimaryButton component={Link} to={wsUrl} onClick={() => onOpenWorkspace(w.work_id)} sx={{ textDecoration: "none", fontSize: "0.8125rem" }}>
            Open in workspace
          </CursorPrimaryButton>
          <CursorSmallButton type="button" onClick={() => handleAddPaperToTarget(w.work_id)} disabled={!tw}>
            Add to target ws
          </CursorSmallButton>
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ p: { xs: 1.5, sm: 2 }, ...mainShellContentSx }}>
      <PageHeader
        eyebrow="Collections"
        title="Workspaces"
        description={
          <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.62)", lineHeight: 1.55 }}>
              Create and switch workspaces. Open a workspace to upload PDFs / text, see papers, and run dedup. Use the left rail for Graph, Ask,
              and Evidence. Browse the global index below only when you need to attach existing works.
            </Typography>
            <WorkIdGlossaryHint variant="corpus" />
          </Box>
        }
        actions={
          continueTarget ? (
            <CursorSmallButton component={Link} to={continueTarget.path} sx={{ textDecoration: "none" }}>
              Continue
            </CursorSmallButton>
          ) : null
        }
      />

      {wsError ? (
        <Alert severity="warning" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {wsError}
        </Alert>
      ) : null}

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 1.5, mb: 2.5 }}>
        <Box sx={{ p: 1.75, borderRadius: "6px", border: "1px solid rgba(99,102,241,0.24)", backgroundColor: "rgba(99,102,241,0.08)" }}>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)", mb: 0.75 }}>Workspaces</Typography>
          {wsLoading ? (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <CircularProgress size={20} />
              <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)" }}>Loading…</Typography>
            </Box>
          ) : workspaces.length === 0 ? (
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.62)" }}>No workspaces yet. Create one below.</Typography>
          ) : (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
              {workspaces.map((ws) => (
                <Box
                  key={ws.id}
                  sx={{
                    display: "flex",
                    flexWrap: "wrap",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 1,
                    borderBottom: "1px solid rgba(255,255,255,0.06)",
                    pb: 0.75,
                  }}
                >
                  <Box sx={{ minWidth: 0 }}>
                    <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>{ws.name || ws.id}</Typography>
                    <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.42)", fontFamily: "monospace" }}>{ws.id}</Typography>
                    <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.45)" }}>
                      {(ws.work_ids || []).length} paper(s)
                    </Typography>
                  </Box>
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                    <CursorSmallButton
                      component={Link}
                      to={`/workspace?workspace_id=${encodeURIComponent(ws.id)}`}
                      onClick={() => setActiveWorkspaceId(ws.id)}
                      sx={{ textDecoration: "none" }}
                    >
                      Open
                    </CursorSmallButton>
                    <CursorSmallButton
                      type="button"
                      onClick={() => {
                        const n = window.prompt("Rename workspace", ws.name || "");
                        if (n != null && String(n).trim()) handleRenameWorkspace(ws.id, String(n).trim());
                      }}
                    >
                      Rename
                    </CursorSmallButton>
                    <CursorSmallButton type="button" onClick={() => handleDeleteWorkspace(ws.id)}>
                      Delete
                    </CursorSmallButton>
                  </Box>
                </Box>
              ))}
            </Box>
          )}
          <Box sx={{ mt: 1.5, display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
            <TextField
              label="New workspace name"
              value={newWsName}
              onChange={(e) => setNewWsName(e.target.value)}
              size="small"
              sx={{ minWidth: 180, "& .MuiInputBase-input": { fontSize: "0.8125rem" } }}
            />
            <CursorPrimaryButton type="button" onClick={() => handleCreateWorkspace()}>
              Create
            </CursorPrimaryButton>
          </Box>
          <Box sx={{ mt: 1.5 }}>
            {workspaces.length ? (
              <FormControl size="small" sx={{ minWidth: 220 }}>
                <InputLabel id="target-ws">Target for “Add to workspace”</InputLabel>
                <Select
                  labelId="target-ws"
                  label='Target for “Add to workspace”'
                  value={targetWorkspaceId}
                  onChange={(e) => {
                    setTargetWorkspaceId(e.target.value);
                    setActiveWorkspaceId(e.target.value);
                  }}
                >
                  {workspaces.map((ws) => (
                    <MenuItem key={ws.id} value={ws.id}>
                      {ws.name || ws.id}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            ) : (
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}>Create a workspace to enable quick-add.</Typography>
            )}
          </Box>
          <Box sx={{ mt: 1.5, display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
            <CursorSmallButton type="button" onClick={exportWorkspacesJson}>
              Export JSON
            </CursorSmallButton>
            <CursorSmallButton component="label" sx={{ cursor: "pointer" }}>
              Import JSON
              <input type="file" accept="application/json" hidden onChange={onImportWorkspaces} />
            </CursorSmallButton>
          </Box>
          <Box sx={{ mt: 1.5, display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
            <TextField
              label="Merge: keep workspace id"
              value={mergeKeep}
              onChange={(e) => setMergeKeep(e.target.value)}
              size="small"
              sx={{ minWidth: 200, "& .MuiInputBase-input": { fontSize: "0.75rem" } }}
            />
            <TextField
              label="Merge: drop workspace id"
              value={mergeDrop}
              onChange={(e) => setMergeDrop(e.target.value)}
              size="small"
              sx={{ minWidth: 200, "& .MuiInputBase-input": { fontSize: "0.75rem" } }}
            />
            <CursorPrimaryButton type="button" disabled={mergeBusy} onClick={() => handleMergeWorkspaces()}>
              Merge
            </CursorPrimaryButton>
          </Box>
        </Box>

        <Box sx={{ p: 1.75, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#1a1a1a" }}>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mb: 0.75 }}>Recent works</Typography>
          {recentWorks.length === 0 ? (
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>No recent works yet.</Typography>
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
                  <CursorSmallButton
                    component={Link}
                    to={tw ? workspacePaperUrl(tw, item.workId) : buildWorkspacePath(item.workId)}
                    sx={{ textDecoration: "none" }}
                  >
                    Open
                  </CursorSmallButton>
                </Box>
              ))}
            </Box>
          )}
        </Box>
      </Box>

      <Accordion
        defaultExpanded={false}
        disableGutters
        sx={{
          mb: 2,
          backgroundColor: "#141414",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: "6px",
          "&:before": { display: "none" },
        }}
      >
        <AccordionSummary sx={{ fontSize: "0.8125rem", fontWeight: 600, color: "rgba(255,255,255,0.85)" }}>
          Browse indexed catalog (attach existing work_id)
        </AccordionSummary>
        <AccordionDetails sx={{ pt: 0 }}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)", mb: 1 }}>Indexed works</Typography>

      <Box component="form" onSubmit={onSearch} sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2, alignItems: "flex-start" }}>
        <TextField
          label="Search (title)"
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
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel id="ws-sort">Sort</InputLabel>
          <Select labelId="ws-sort" label="Sort" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <MenuItem value="api">API order</MenuItem>
            <MenuItem value="title">Title (A–Z)</MenuItem>
            <MenuItem value="year_desc">Year (newest)</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel id="ws-view">View</InputLabel>
          <Select labelId="ws-view" label="View" value={viewDensity} onChange={(e) => setViewDensity(e.target.value)}>
            <MenuItem value="cards">Cards</MenuItem>
            <MenuItem value="compact">Compact</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel id="ws-sem">Semantic</InputLabel>
          <Select labelId="ws-sem" label="Semantic" value={semanticFilter} onChange={(e) => setSemanticFilter(e.target.value)}>
            <MenuItem value="all">All works</MenuItem>
            <MenuItem value="ready">Semantic ready</MenuItem>
            <MenuItem value="not_ready">Not semantic-ready</MenuItem>
          </Select>
        </FormControl>
        <TextField label="Year min" value={yearMin} onChange={(e) => setYearMin(e.target.value)} size="small" type="number" sx={{ width: 100 }} />
        <TextField label="Year max" value={yearMax} onChange={(e) => setYearMax(e.target.value)} size="small" type="number" sx={{ width: 100 }} />
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
          Total in index: {total}
          {items.length < total ? ` · Loaded: ${items.length}` : null}
        </Typography>
      )}

      <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>{sortedItems.map(renderWorkRow)}</Box>

      {!loading && !error && canLoadMore ? (
        <Box sx={{ mt: 2 }}>
          <CursorPrimaryButton type="button" disabled={loadingMore} onClick={() => loadMore().catch(() => {})}>
            {loadingMore ? "Loading…" : "Load more"}
          </CursorPrimaryButton>
        </Box>
      ) : null}
        </AccordionDetails>
      </Accordion>
    </Box>
  );
}
