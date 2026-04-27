import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Popover from "@mui/material/Popover";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import CheckOutlinedIcon from "@mui/icons-material/CheckOutlined";
import CloseOutlinedIcon from "@mui/icons-material/CloseOutlined";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import VpnKeyOutlinedIcon from "@mui/icons-material/VpnKeyOutlined";

import { CursorIconAction, CursorIconButton } from "../components/common/index.js";
import PageHeader from "../components/layout/PageHeader.jsx";
import { useWorkspaceContext } from "../components/layout/useWorkspaceContext.js";
import GraphWorkspacePanel from "../components/graph/GraphWorkspacePanel.jsx";
import { GraphMissingWorkCallout } from "../components/graph/graphShellStates.jsx";
import { persistWorkId } from "./WorkspacePage/utils/workContext.js";
import {
  mergeTraceabilityStateWithHashSelection,
  readTraceabilityState,
  replaceHashTraceabilitySelection,
} from "../components/work/traceabilityState.js";
import { useHashTraceabilityGraphSelection } from "../components/work/useHashTraceabilityGraphSelection.js";
import { readGraphPageLayoutFlags, preserveGraphPageOptionalParams } from "./graphPageUrl.js";
import { useI18n } from "../i18n/useI18n.js";

const LS_GRAPH_PAGE_ABOUT = "graphPageAboutOpen";

export default function GraphPage() {
  const { t } = useI18n();
  const { getLastWorkspaceHref, activeWorkspaceId } = useWorkspaceContext();
  const [searchParams, setSearchParams] = useSearchParams();
  const initial = searchParams.get("work_id") || "";
  const [workIdInput, setWorkIdInput] = useState(initial);
  const traceRouter = useMemo(() => readTraceabilityState(searchParams), [searchParams]);
  const hashSel = useHashTraceabilityGraphSelection();
  const trace = useMemo(() => mergeTraceabilityStateWithHashSelection(traceRouter, hashSel), [traceRouter, hashSel]);
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
  const graphTargetKey = `${workIdTrimmed}|${effectiveWorkspaceId}`;
  const [selectedTrace, setSelectedTrace] = useState(() => ({
    targetKey: graphTargetKey,
    nodeId: trace.nodeId,
    edgeId: trace.edgeId,
  }));

  useEffect(() => {
    // Sync local selection with URL/hash when scope or deep link changes (replaceState bypasses Router).
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional URL↔state sync
    setSelectedTrace((prev) => {
      if (prev.targetKey !== graphTargetKey) {
        return { targetKey: graphTargetKey, nodeId: trace.nodeId, edgeId: trace.edgeId };
      }
      if (prev.nodeId === trace.nodeId && prev.edgeId === trace.edgeId) return prev;
      return { ...prev, nodeId: trace.nodeId, edgeId: trace.edgeId };
    });
  }, [graphTargetKey, trace.nodeId, trace.edgeId]);

  const selectedNodeId = selectedTrace.targetKey === graphTargetKey ? selectedTrace.nodeId : trace.nodeId;
  const selectedEdgeId = selectedTrace.targetKey === graphTargetKey ? selectedTrace.edgeId : trace.edgeId;
  const labMode = searchParams.get("lab") === "1";
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
      params.set("work_id", next);
      preserveGraphPageOptionalParams(params, searchParams);
      setSearchParams(params);
    } else {
      const cleared = new URLSearchParams();
      preserveGraphPageOptionalParams(cleared, searchParams);
      setSearchParams(cleared);
    }
    setLoadAnchor(null);
  }

  const handleReconcileSelection = useCallback(
    ({ nodeId, edgeId }) => {
      setSelectedTrace({ targetKey: graphTargetKey, nodeId, edgeId });
      replaceHashTraceabilitySelection({ nodeId, edgeId });
    },
    [graphTargetKey],
  );

  function handleSelectNode(nodeId) {
    const next = String(nodeId || "").trim();
    setSelectedTrace({ targetKey: graphTargetKey, nodeId: next, edgeId: "" });
    replaceHashTraceabilitySelection({ nodeId: next, edgeId: "" });
  }

  function handleSelectEdge(edgeId) {
    const next = String(edgeId || "").trim();
    setSelectedTrace({ targetKey: graphTargetKey, nodeId: "", edgeId: next });
    replaceHashTraceabilitySelection({ nodeId: "", edgeId: next });
  }

  return (
    <Box
      sx={{
        flex: 1,
        minHeight: 0,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        px: 1,
        pt: 0.75,
        pb: 0.5,
        width: "100%",
        maxWidth: "100%",
        boxSizing: "border-box",
      }}
    >
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
        <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.9)" }}>{t("graph.toolbar.title")}</Typography>
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
              backgroundColor: "#1a1a1a",
              border: "1px solid rgba(255,255,255,0.08)",
            },
          },
        }}
      >
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mb: 1 }}>{t("graph.popover.hint")}</Typography>
        <Box component="form" onSubmit={applyWorkId} sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          <TextField
            label={t("reader.workIdLabel")}
            value={workIdInput}
            onChange={(ev) => setWorkIdInput(ev.target.value)}
            size="small"
            fullWidth
            sx={{
              "& .MuiInputBase-input": { fontSize: "0.8125rem" },
              "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
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
          selectedNodeId={selectedNodeId}
          onSelectNode={handleSelectNode}
          selectedEdgeId={selectedEdgeId}
          onSelectEdge={handleSelectEdge}
          onReconcileSelection={handleReconcileSelection}
          mode="standalone"
          compactLayout={compactLayout}
          focusLayout={focus}
          labMode={labMode}
          title=""
          subtitle={null}
          traceContext={{
            chunkFingerprint: trace.chunkFingerprint,
            section: trace.section,
            citation: trace.citation,
            edgeId: selectedEdgeId,
          }}
        />
      </Box>
    </Box>
  );
}
