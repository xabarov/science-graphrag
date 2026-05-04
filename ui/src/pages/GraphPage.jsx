import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Collapse from "@mui/material/Collapse";
import Popover from "@mui/material/Popover";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import CheckOutlinedIcon from "@mui/icons-material/CheckOutlined";
import CloseOutlinedIcon from "@mui/icons-material/CloseOutlined";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import VpnKeyOutlinedIcon from "@mui/icons-material/VpnKeyOutlined";

import { CursorIconAction, CursorIconButton } from "../components/common/index.js";
import PageHeader from "../components/layout/PageHeader.jsx";
import { useWorkspaceContext } from "../components/layout/useWorkspaceContext.js";
import GraphWorkspacePanel from "../components/graph/workspace/GraphWorkspacePanel.jsx";
import { GraphMissingWorkCallout } from "../components/graph/shell/graphShellStates.jsx";
import { persistWorkId } from "./WorkspacePage/utils/workContext.js";
import {
  GRAPH_PAGE_QUERY_KEYS,
  mergeTraceabilityParams,
  preserveGraphPageOptionalParams,
  readGraphPageLayoutFlags,
  readTraceabilityState,
  TRACEABILITY_QUERY_KEYS,
} from "../routing/index.js";
import { useI18n } from "../i18n/useI18n.js";

const LS_GRAPH_PAGE_ABOUT = "graphPageAboutOpen";

const GRAPH_SEARCH_MERGE_OPTS = { includeTab: false };

export default function GraphPage() {
  const theme = useTheme();
  const tk = theme.appTokens;
  const { t } = useI18n();
  const { getLastWorkspaceHref, activeWorkspaceId } = useWorkspaceContext();
  const [searchParams, setSearchParams] = useSearchParams();
  const initial = searchParams.get(TRACEABILITY_QUERY_KEYS.workId) || "";
  const [workIdInput, setWorkIdInput] = useState(initial);
  const trace = useMemo(() => readTraceabilityState(searchParams), [searchParams]);
  const workId = trace.workId;
  const workspaceId = trace.workspaceId;
  const workspaceIdFromUrl = workspaceId.trim();
  const workIdTrimmed = workId.trim();
  // If the URL names a work but omits workspace_id, do not fall back to the shell's active
  // workspace: useGraphWorkspaceData would load the full workspace graph and ignore work scope
  // (e.g. Graph link on a paper card uses /graph?work_id=... only).
  const effectiveWorkspaceId = workIdTrimmed
    ? workspaceIdFromUrl
    : workspaceIdFromUrl || String(activeWorkspaceId || "").trim();

  const labMode = searchParams.get(GRAPH_PAGE_QUERY_KEYS.lab) === "1";
  const { compact, focus, compactLayout } = readGraphPageLayoutFlags(searchParams);
  const chromeDense = compact || focus;

  const [aboutOpen, setAboutOpen] = useState(() => {
    if (typeof window === "undefined") return false;
    if (chromeDense) return false;
    return window.localStorage.getItem(LS_GRAPH_PAGE_ABOUT) === "1";
  });
  const [loadAnchor, setLoadAnchor] = useState(null);

  useEffect(() => {
    setWorkIdInput(workId);
  }, [workId]);

  useEffect(() => {
    if (workId.trim()) persistWorkId(workId);
  }, [workId]);

  useEffect(() => {
    if (chromeDense) setAboutOpen(false);
  }, [chromeDense]);

  useEffect(() => {
    try {
      window.localStorage.setItem(LS_GRAPH_PAGE_ABOUT, aboutOpen ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [aboutOpen]);

  function applyWorkId(e) {
    e?.preventDefault?.();
    const next = workIdInput.trim();
    if (next) {
      persistWorkId(next);
      const params = new URLSearchParams();
      params.set(TRACEABILITY_QUERY_KEYS.workId, next);
      preserveGraphPageOptionalParams(params, searchParams);
      setSearchParams(params);
    } else {
      const cleared = new URLSearchParams();
      preserveGraphPageOptionalParams(cleared, searchParams);
      setSearchParams(cleared);
    }
    setLoadAnchor(null);
  }

  // Graph selection is encoded in HashRouter search params via React Router (not replaceState on
  // the raw hash). Functional updates avoid stale closures on rapid clicks. If profiling shows
  // excess re-renders, debounce only setSearchParams while keeping panel selection local.
  const handleReconcileSelection = useCallback(({ nodeId, edgeId }) => {
    setSearchParams(
      (prev) => mergeTraceabilityParams(prev, { nodeId, edgeId }, GRAPH_SEARCH_MERGE_OPTS),
      { replace: true },
    );
  }, [setSearchParams]);

  const handleSelectNode = useCallback(
    (nodeId) => {
      const next = String(nodeId || "").trim();
      setSearchParams(
        (prev) => mergeTraceabilityParams(prev, { nodeId: next, edgeId: "" }, GRAPH_SEARCH_MERGE_OPTS),
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const handleSelectEdge = useCallback(
    (edgeId) => {
      const next = String(edgeId || "").trim();
      setSearchParams(
        (prev) => mergeTraceabilityParams(prev, { nodeId: "", edgeId: next }, GRAPH_SEARCH_MERGE_OPTS),
        { replace: true },
      );
    },
    [setSearchParams],
  );

  return (
    <Box
      sx={{
        flex: 1,
        minHeight: 0,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        px: chromeDense ? 0.75 : 1,
        pt: chromeDense ? 0.25 : 0.75,
        pb: chromeDense ? 0.25 : 0.5,
        width: "100%",
        maxWidth: "100%",
        boxSizing: "border-box",
      }}
    >
      {!chromeDense ? (
        <Box
          sx={{
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            gap: 0.75,
            flexWrap: "wrap",
            mb: 0.5,
          }}
        >
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: tk.text.primary }}>{t("graph.toolbar.title")}</Typography>
          <Box sx={{ flex: 1, minWidth: 8 }} />
          <Tooltip title={t("graph.toolbar.loadTooltip")} placement="bottom">
            <CursorIconButton
              aria-label={t("graph.toolbar.loadAria")}
              aria-haspopup="true"
              aria-expanded={Boolean(loadAnchor)}
              onClick={(ev) => setLoadAnchor(ev.currentTarget)}
            >
              <VpnKeyOutlinedIcon sx={{ fontSize: "1.05rem" }} />
            </CursorIconButton>
          </Tooltip>
          <Tooltip title={t("graph.toolbar.aboutTooltip")} placement="bottom">
            <CursorIconButton
              type="button"
              onClick={() => setAboutOpen((v) => !v)}
              aria-expanded={aboutOpen}
              aria-controls="graph-page-about"
              aria-label={t("graph.toolbar.aboutAria")}
            >
              <InfoOutlinedIcon sx={{ fontSize: "1.05rem" }} />
            </CursorIconButton>
          </Tooltip>
        </Box>
      ) : null}

      <Popover
        open={Boolean(loadAnchor)}
        anchorEl={loadAnchor}
        onClose={() => setLoadAnchor(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        slotProps={{
          paper: {
            sx: {
              mt: 0.75,
              p: 1.5,
              minWidth: 280,
              maxWidth: 420,
              backgroundColor: tk.surface.panel,
              border: `1px solid ${tk.border.default}`,
            },
          },
        }}
      >
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, mb: 1 }}>{t("graph.popover.hint")}</Typography>
        <Box component="form" onSubmit={applyWorkId} sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          <TextField
            label={t("reader.workIdLabel")}
            value={workIdInput}
            onChange={(ev) => setWorkIdInput(ev.target.value)}
            size="small"
            fullWidth
            sx={{
              "& .MuiInputBase-input": { fontSize: "0.8125rem" },
              "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: tk.text.secondary },
            }}
          />
          <Box sx={{ display: "flex", gap: 0.75, justifyContent: "flex-end" }}>
            <CursorIconAction type="button" title={t("graph.popover.cancel")} onClick={() => setLoadAnchor(null)}>
              <CloseOutlinedIcon sx={{ fontSize: "1.1rem" }} />
            </CursorIconAction>
            <CursorIconAction type="submit" title={t("graph.popover.apply")}>
              <CheckOutlinedIcon sx={{ fontSize: "1.1rem" }} />
            </CursorIconAction>
          </Box>
        </Box>
      </Popover>

      <Collapse in={aboutOpen}>
        <Box id="graph-page-about" sx={{ flexShrink: 0, mb: 0.5 }}>
          <PageHeader
            eyebrow={t("graph.about.eyebrow")}
            title={t("graph.about.title")}
            description={t("graph.about.description")}
          />
        </Box>
      </Collapse>

      {!workId.trim() && !effectiveWorkspaceId ? (
        <Box sx={{ flexShrink: 0, mb: 0.5 }}>
          <GraphMissingWorkCallout
            title={t("graph.missing.title")}
            description={t("graph.missing.description")}
            footnote={t("graph.missing.footnote")}
          />
          <Box sx={{ mt: 1.5 }}>
            <CursorIconAction component={Link} to={getLastWorkspaceHref()} title={t("graph.openLastWorkspace")}>
              <HubOutlinedIcon sx={{ fontSize: "1.15rem" }} />
            </CursorIconAction>
          </Box>
        </Box>
      ) : null}

      <Box sx={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <GraphWorkspacePanel
          workId={workId}
          workspaceId={effectiveWorkspaceId}
          selectedNodeId={trace.nodeId}
          onSelectNode={handleSelectNode}
          selectedEdgeId={trace.edgeId}
          onSelectEdge={handleSelectEdge}
          onReconcileSelection={handleReconcileSelection}
          mode="standalone"
          compactLayout={compactLayout}
          focusLayout={focus}
          labMode={labMode}
          title=""
          subtitle={null}
          standaloneToolbarLeading={
            chromeDense ? (
              <Stack direction="row" alignItems="center" gap={0.25}>
                <Tooltip title={t("graph.toolbar.loadTooltip")} placement="bottom">
                  <CursorIconButton
                    aria-label={t("graph.toolbar.loadAria")}
                    aria-haspopup="true"
                    aria-expanded={Boolean(loadAnchor)}
                    onClick={(ev) => setLoadAnchor(ev.currentTarget)}
                  >
                    <VpnKeyOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                  </CursorIconButton>
                </Tooltip>
                <Tooltip title={t("graph.toolbar.aboutTooltip")} placement="bottom">
                  <CursorIconButton
                    type="button"
                    onClick={() => setAboutOpen((v) => !v)}
                    aria-expanded={aboutOpen}
                    aria-controls="graph-page-about"
                    aria-label={t("graph.toolbar.aboutAria")}
                  >
                    <InfoOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                  </CursorIconButton>
                </Tooltip>
              </Stack>
            ) : null
          }
          traceContext={{
            chunkFingerprint: trace.chunkFingerprint,
            section: trace.section,
            citation: trace.citation,
          }}
        />
      </Box>
    </Box>
  );
}
