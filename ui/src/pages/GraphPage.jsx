import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Popover from "@mui/material/Popover";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import CheckOutlinedIcon from "@mui/icons-material/CheckOutlined";
import CloseOutlinedIcon from "@mui/icons-material/CloseOutlined";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import VpnKeyOutlinedIcon from "@mui/icons-material/VpnKeyOutlined";

import { CursorIconAction, CursorIconButton } from "../components/common/index.js";
import PageHeader from "../components/layout/PageHeader.jsx";
import { useWorkspaceContext } from "../components/layout/WorkspaceContext.jsx";
import GraphWorkspacePanel from "../components/graph/GraphWorkspacePanel.jsx";
import { GraphMissingWorkCallout } from "../components/graph/graphShellStates.jsx";
import { persistWorkId } from "./WorkspacePage/utils/workContext.js";
import { mergeTraceabilityParams, readTraceabilityState } from "../components/work/traceabilityState.js";
import { readGraphPageLayoutFlags, preserveGraphPageOptionalParams } from "./graphPageUrl.js";
import { useI18n } from "../i18n/I18nContext.jsx";

const LS_GRAPH_PAGE_ABOUT = "graphPageAboutOpen";

export default function GraphPage() {
  const { t } = useI18n();
  const { getLastWorkspaceHref, activeWorkspaceId } = useWorkspaceContext();
  const [searchParams, setSearchParams] = useSearchParams();
  const initial = searchParams.get("work_id") || "";
  const [workIdInput, setWorkIdInput] = useState(initial);
  const trace = readTraceabilityState(searchParams);
  const workId = trace.workId;
  const workspaceId = trace.workspaceId;
  const effectiveWorkspaceId = (workspaceId || activeWorkspaceId || "").trim();
  const selectedNodeId = trace.nodeId;
  const selectedEdgeId = trace.edgeId;
  const labMode = searchParams.get("lab") === "1";
  const graphDepth = searchParams.get("graph_depth") === "2" ? 2 : 1;
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

  function handleSelectNode(nodeId) {
    const params = mergeTraceabilityParams(searchParams, { nodeId, edgeId: "" });
    setSearchParams(params, { replace: false });
  }

  function handleSelectEdge(edgeId) {
    const params = mergeTraceabilityParams(searchParams, { edgeId, nodeId: "" });
    setSearchParams(params, { replace: false });
  }

  function handleStandaloneGraphDepth(_ev, nextDepth) {
    if (nextDepth == null) return;
    const params = new URLSearchParams(searchParams);
    if (nextDepth === 2) params.set("graph_depth", "2");
    else params.delete("graph_depth");
    setSearchParams(params, { replace: true });
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
        {workId.trim() && !effectiveWorkspaceId ? (
          <ToggleButtonGroup
            size="small"
            exclusive
            value={graphDepth}
            onChange={handleStandaloneGraphDepth}
            sx={{
              "& .MuiToggleButton-root": {
                fontSize: "0.7rem",
                py: 0.25,
                px: 0.75,
                color: "rgba(255,255,255,0.55)",
                borderColor: "rgba(255,255,255,0.12)",
              },
              "& .Mui-selected": { color: "rgba(129,140,248,0.95)", backgroundColor: "rgba(99,102,241,0.12)" },
            }}
          >
            <ToggleButton value={1} aria-label={t("graph.standaloneDepth.depth1Aria")}>
              {t("graph.wsToolbar.depth1")}
            </ToggleButton>
            <ToggleButton value={2} aria-label={t("graph.standaloneDepth.depth2Aria")}>
              {t("graph.wsToolbar.depth2")}
            </ToggleButton>
          </ToggleButtonGroup>
        ) : null}
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
          mode="standalone"
          compactLayout={compactLayout}
          focusLayout={focus}
          labMode={labMode}
          standaloneWorkGraphDepth={graphDepth}
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
