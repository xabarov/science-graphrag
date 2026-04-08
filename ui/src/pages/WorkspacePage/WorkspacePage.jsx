import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";

import { CursorPrimaryButton, CursorSmallButton } from "../../components/common/index.js";
import PageHeader from "../../components/layout/PageHeader.jsx";
import { getWorkDetail } from "../../services/researchApi.js";
import { getLastWorkId, normalizeWorkspaceTab, persistWorkId, persistWorkspaceTab } from "./utils/workContext.js";
import { WORKSPACE_TAB_CONFIG, workspaceTabIndex, workspaceTabSlugFromIndex } from "./WorkspaceTabs.jsx";
import OverviewTab from "./tabs/OverviewTab.jsx";
import ReaderTab from "./tabs/ReaderTab.jsx";
import GraphTab from "./tabs/GraphTab.jsx";
import AskTab from "./tabs/AskTab.jsx";
import EvidenceTab from "./tabs/EvidenceTab.jsx";
import { rememberRecentWork } from "../HomePage/homeState.js";

export default function WorkspacePage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const workId = (searchParams.get("work_id") || "").trim();
  const tabSlug = normalizeWorkspaceTab(searchParams.get("tab"));
  const tabIndex = workspaceTabIndex(tabSlug);

  const [headerTitle, setHeaderTitle] = useState("");
  const [headerLoading, setHeaderLoading] = useState(false);

  const setTabParams = useCallback(
    (nextTabSlug, nextWorkId = workId) => {
      const params = new URLSearchParams();
      const wid = String(nextWorkId || "").trim();
      if (wid) params.set("work_id", wid);
      params.set("tab", normalizeWorkspaceTab(nextTabSlug));
      setSearchParams(params, { replace: false });
    },
    [setSearchParams, workId],
  );

  /** Restore last work when opening /workspace with no work_id */
  useEffect(() => {
    if (workId) return;
    const last = getLastWorkId();
    if (last) {
      const params = new URLSearchParams();
      params.set("work_id", last);
      params.set("tab", tabSlug);
      navigate(`/workspace?${params.toString()}`, { replace: true });
    }
  }, [workId, navigate, tabSlug]);

  useEffect(() => {
    if (workId) persistWorkId(workId);
  }, [workId]);

  useEffect(() => {
    persistWorkspaceTab(tabSlug);
  }, [tabSlug]);

  useEffect(() => {
    if (!workId) {
      setHeaderTitle("");
      return;
    }
    let cancelled = false;
    (async () => {
      setHeaderLoading(true);
      try {
        const res = await getWorkDetail(workId);
        if (cancelled) return;
        const t = res.data?.title;
        setHeaderTitle(typeof t === "string" && t.trim() ? t : "");
        rememberRecentWork({
          workId,
          title: typeof t === "string" ? t : "",
          year: res.data?.year ?? null,
          tab: tabSlug,
        });
      } catch {
        if (!cancelled) setHeaderTitle("");
      } finally {
        if (!cancelled) setHeaderLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workId, tabSlug]);

  const handleTabChange = (_e, value) => {
    setTabParams(workspaceTabSlugFromIndex(value), workId);
  };

  const emptyState = useMemo(
    () => (
      <Box sx={{ maxWidth: 560, mt: 2 }}>
        <Alert severity="info" sx={{ fontSize: "0.8125rem", mb: 2, backgroundColor: "rgba(99,102,241,0.08)", color: "rgba(255,255,255,0.85)" }}>
          No active work. Open the corpus and choose a paper to start a workspace session.
        </Alert>
        <CursorPrimaryButton component={Link} to="/corpus" sx={{ textDecoration: "none" }}>
          Go to Corpus
        </CursorPrimaryButton>
        <CursorSmallButton component={Link} to="/" sx={{ textDecoration: "none", ml: 1 }}>
          Home
        </CursorSmallButton>
      </Box>
    ),
    [],
  );

  return (
    <Box sx={{ p: 2, maxWidth: 1100 }}>
      <PageHeader
        eyebrow="Workspace-first flow"
        title="Workspace"
        description={
          workId ? (
            <>
              {headerLoading ? (
                <Box sx={{ display: "inline-flex", alignItems: "center", gap: 1 }}>
                  <CircularProgress size={18} sx={{ color: "rgba(129,140,248,0.9)" }} />
                  <span>Loading context…</span>
                </Box>
              ) : (
                <>
                  {headerTitle || "(no title)"}
                  <br />
                  <span style={{ color: "rgba(255,255,255,0.45)", fontFamily: "monospace", fontSize: "0.75rem" }}>{workId}</span>
                </>
              )}
            </>
          ) : (
            "Open a work and switch between overview, reading, graph, ask, and evidence without leaving the active research context."
          )
        }
        actions={
          <>
            <CursorSmallButton component={Link} to="/corpus" sx={{ textDecoration: "none" }}>
              Corpus
            </CursorSmallButton>
            <CursorSmallButton component={Link} to="/" sx={{ textDecoration: "none" }}>
              Home
            </CursorSmallButton>
            {workId ? (
              <CursorSmallButton component={Link} to={`/graph?work_id=${encodeURIComponent(workId)}`} sx={{ textDecoration: "none" }}>
                Graph
              </CursorSmallButton>
            ) : null}
          </>
        }
      />

      <Tabs
        value={tabIndex}
        onChange={handleTabChange}
        sx={{
          minHeight: 36,
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          mb: 2,
          "& .MuiTab-root": {
            minHeight: 36,
            fontSize: "0.8125rem",
            fontWeight: 500,
            textTransform: "none",
            color: "rgba(255,255,255,0.6)",
            "&:focus-visible": {
              outline: "2px solid rgba(129, 140, 248, 0.75)",
              outlineOffset: 2,
            },
          },
          "& .Mui-selected": { color: "rgba(255,255,255,0.9) !important" },
          "& .MuiTabs-indicator": { backgroundColor: "rgba(99, 102, 241, 0.8)", height: 2 },
        }}
      >
        {WORKSPACE_TAB_CONFIG.map((t) => (
          <Tab key={t.slug} label={t.label} disabled={!workId} />
        ))}
      </Tabs>

      {!workId ? (
        emptyState
      ) : (
        <>
          {tabSlug === "overview" ? <OverviewTab workId={workId} /> : null}
          {tabSlug === "reader" ? <ReaderTab workId={workId} /> : null}
          {tabSlug === "graph" ? <GraphTab workId={workId} /> : null}
          {tabSlug === "ask" ? <AskTab workId={workId} /> : null}
          {tabSlug === "evidence" ? <EvidenceTab workId={workId} /> : null}
        </>
      )}
    </Box>
  );
}
