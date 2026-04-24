import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import Chip from "@mui/material/Chip";

import { CursorPrimaryButton, CursorSmallButton } from "../components/common/index.js";
import PageHeader from "../components/layout/PageHeader.jsx";
import WorkIdGlossaryHint from "../components/layout/WorkIdGlossaryHint.jsx";
import { mainShellContentSx } from "../components/layout/mainShellContentSx.js";
import { useI18n } from "../i18n/I18nContext.jsx";
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
import IndexedWorksBrowser from "./WorkspacesPage/IndexedWorksBrowser.jsx";
import WorkspaceCollectionPanel from "./WorkspacesPage/WorkspaceCollectionPanel.jsx";
import WorkspaceRecentPanel from "./WorkspacesPage/WorkspaceRecentPanel.jsx";

const PAGE_SIZE = 40;

export default function WorkspacesPage() {
  const { t, intlLocale } = useI18n();
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
  const [newWsName, setNewWsName] = useState(() => t("workspaces.defaultNewName"));
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
      workspaceId: targetWorkspaceId || "",
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
    if (!window.confirm(t("workspaces.confirmDelete"))) return;
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
      setWsError(t("workspaces.errSelectTarget"));
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
        setWsError(arr.length ? t("workspaces.importPreview", { count: arr.length }) : t("workspaces.importEmpty"));
      } catch {
        setWsError(t("workspaces.importInvalid"));
      }
    };
    reader.readAsText(f);
    ev.target.value = "";
  }

  const sortedItems = useMemo(() => {
    const arr = [...items];
    if (sortBy === "title") {
      arr.sort((a, b) =>
        String(a.title || "").localeCompare(String(b.title || ""), intlLocale, { sensitivity: "base" }),
      );
    } else if (sortBy === "year_desc") {
      arr.sort((a, b) => (Number(b.year) || 0) - (Number(a.year) || 0));
    }
    return arr;
  }, [items, sortBy, intlLocale]);

  const canLoadMore = !loading && items.length < total;
  const tw = targetWorkspaceId;

  function renderWorkRow(w) {
    const wsUrl = tw ? buildWorkspacePath(w.work_id, "overview", { workspaceId: tw }) : buildWorkspacePath(w.work_id);
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
              {w.title || t("workspaces.row.noTitle")}
            </Typography>
            <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.45)" }} noWrap>
              {w.year != null ? `${w.year} · ` : ""}
              {w.work_id}
            </Typography>
          </Box>
          <CursorPrimaryButton component={Link} to={wsUrl} onClick={() => onOpenWorkspace(w.work_id)} sx={{ textDecoration: "none", fontSize: "0.75rem", minHeight: 28 }}>
            {t("workspaces.row.workspace")}
          </CursorPrimaryButton>
          <CursorSmallButton type="button" onClick={() => handleAddPaperToTarget(w.work_id)} disabled={!tw}>
            {t("workspaces.row.addToTarget")}
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
          {w.title || t("workspaces.row.noTitle")}
        </Typography>
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mt: 0.5 }}>
          {w.year != null ? `${w.year} · ` : ""}
          {w.work_id}
        </Typography>
        <Box sx={{ mt: 0.9, display: "flex", flexWrap: "wrap", gap: 0.75 }}>
          {w.year != null ? (
            <Chip label={t("workspaces.chip.year", { year: w.year })} size="small" sx={{ height: 22, fontSize: "0.6875rem" }} />
          ) : null}
          {w.has_semantic_layer ? (
            <Chip label={t("workspaces.chip.semanticReady")} size="small" sx={{ height: 22, fontSize: "0.6875rem" }} />
          ) : null}
        </Box>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mt: 1.25, alignItems: "center" }}>
          <CursorPrimaryButton component={Link} to={wsUrl} onClick={() => onOpenWorkspace(w.work_id)} sx={{ textDecoration: "none", fontSize: "0.8125rem" }}>
            {t("workspaces.row.openInWs")}
          </CursorPrimaryButton>
          <CursorSmallButton type="button" onClick={() => handleAddPaperToTarget(w.work_id)} disabled={!tw}>
            {t("workspaces.row.addToTargetWs")}
          </CursorSmallButton>
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ p: { xs: 1.5, sm: 2 }, ...mainShellContentSx }}>
      <PageHeader
        eyebrow={t("workspaces.header.eyebrow")}
        title={t("workspaces.header.title")}
        description={
          <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.62)", lineHeight: 1.55 }}>
              {t("workspaces.header.desc")}
            </Typography>
            <WorkIdGlossaryHint variant="corpus" />
          </Box>
        }
        actions={
          continueTarget ? (
            <CursorSmallButton component={Link} to={continueTarget.path} sx={{ textDecoration: "none" }}>
              {t("workspaces.continue")}
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
        <WorkspaceCollectionPanel
          workspaces={workspaces}
          wsLoading={wsLoading}
          newWsName={newWsName}
          onNewWsNameChange={setNewWsName}
          onCreateWorkspace={handleCreateWorkspace}
          targetWorkspaceId={targetWorkspaceId}
          onTargetWorkspaceChange={setTargetWorkspaceId}
          onRenameWorkspace={handleRenameWorkspace}
          onDeleteWorkspace={handleDeleteWorkspace}
          mergeKeep={mergeKeep}
          mergeDrop={mergeDrop}
          mergeBusy={mergeBusy}
          onMergeKeepChange={setMergeKeep}
          onMergeDropChange={setMergeDrop}
          onMergeWorkspaces={handleMergeWorkspaces}
          exportWorkspacesJson={exportWorkspacesJson}
          onImportWorkspaces={onImportWorkspaces}
        />
        <WorkspaceRecentPanel recentWorks={recentWorks} fallbackWorkspaceId={tw} />
      </Box>

      <IndexedWorksBrowser
        q={q}
        onQChange={setQ}
        onSearch={onSearch}
        loading={loading}
        loadingMore={loadingMore}
        error={error}
        items={items}
        total={total}
        canLoadMore={canLoadMore}
        onLoadMore={loadMore}
        sortBy={sortBy}
        onSortByChange={setSortBy}
        viewDensity={viewDensity}
        onViewDensityChange={setViewDensity}
        semanticFilter={semanticFilter}
        onSemanticFilterChange={setSemanticFilter}
        yearMin={yearMin}
        yearMax={yearMax}
        onYearMinChange={setYearMin}
        onYearMaxChange={setYearMax}
        sortedItems={sortedItems}
        renderWorkRow={renderWorkRow}
      />
    </Box>
  );
}
