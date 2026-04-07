import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";

import { CursorPrimaryButton, CursorSmallButton } from "../../components/common/index.js";
import { getWorkDetail } from "../../services/researchApi.js";
import { getLastWorkId, normalizeWorkspaceTab, persistWorkId } from "./utils/workContext.js";
import { WORKSPACE_TAB_CONFIG, workspaceTabIndex, workspaceTabSlugFromIndex } from "./WorkspaceTabs.jsx";
import OverviewTab from "./tabs/OverviewTab.jsx";
import ReaderTab from "./tabs/ReaderTab.jsx";
import AskTab from "./tabs/AskTab.jsx";
import EvidenceTab from "./tabs/EvidenceTab.jsx";

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
      } catch {
        if (!cancelled) setHeaderTitle("");
      } finally {
        if (!cancelled) setHeaderLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workId]);

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
      </Box>
    ),
    [],
  );

  return (
    <Box sx={{ p: 2, maxWidth: 1100 }}>
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "flex-start", justifyContent: "space-between", gap: 1, mb: 1 }}>
        <Box>
          <Typography sx={{ fontWeight: 600, color: "rgba(255,255,255,0.9)" }}>Workspace</Typography>
          {workId ? (
            <Box sx={{ mt: 0.5 }}>
              {headerLoading ? (
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <CircularProgress size={18} sx={{ color: "rgba(129,140,248,0.9)" }} />
                  <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>Loading context…</Typography>
                </Box>
              ) : (
                <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)", maxWidth: 720 }}>
                  {headerTitle || "(no title)"}
                </Typography>
              )}
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.25, fontFamily: "monospace" }}>
                {workId}
              </Typography>
            </Box>
          ) : null}
        </Box>
        {workId ? (
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
            <CursorSmallButton component={Link} to="/corpus" sx={{ textDecoration: "none" }}>
              Corpus
            </CursorSmallButton>
            <CursorSmallButton component={Link} to={`/graph?work_id=${encodeURIComponent(workId)}`} sx={{ textDecoration: "none" }}>
              Graph
            </CursorSmallButton>
          </Box>
        ) : null}
      </Box>

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
          {tabSlug === "ask" ? <AskTab workId={workId} /> : null}
          {tabSlug === "evidence" ? <EvidenceTab workId={workId} /> : null}
        </>
      )}
    </Box>
  );
}
