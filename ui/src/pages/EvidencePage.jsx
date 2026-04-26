import React, { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import FolderOpenOutlinedIcon from "@mui/icons-material/FolderOpenOutlined";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import PlayArrowOutlinedIcon from "@mui/icons-material/PlayArrowOutlined";

import { CursorIconAction } from "../components/common/index.js";
import PageHeader from "../components/layout/PageHeader.jsx";
import { useWorkspaceContext } from "../components/layout/useWorkspaceContext.js";
import { isExplicitAdminMode } from "../components/layout/adminVisibility.js";
import { mainShellContentSx } from "../components/layout/mainShellContentSx.js";
import { useI18n } from "../i18n/useI18n.js";
import EvidenceWorkBody from "../components/work/EvidenceWorkBody.jsx";
import { persistWorkId } from "./WorkspacePage/utils/workContext.js";
import { buildWorkspaceTracePath, readTraceabilityState } from "../components/work/traceabilityState.js";

export default function EvidencePage() {
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const initial = searchParams.get("work_id") || "";
  const [workIdInput, setWorkIdInput] = useState(initial);
  const { getLastWorkspaceHref, activeWorkspaceId } = useWorkspaceContext();

  const workId = searchParams.get("work_id") || "";
  const trace = readTraceabilityState(searchParams);
  const workspaceIdInUrl = (searchParams.get("workspace_id") || "").trim();
  const effectiveWorkspaceId = useMemo(
    () => workspaceIdInUrl || trace.workspaceId || (activeWorkspaceId || "").trim(),
    [workspaceIdInUrl, trace.workspaceId, activeWorkspaceId],
  );

  const showDevWorkIdForm = searchParams.get("dev") === "1" || isExplicitAdminMode();

  useEffect(() => {
    setWorkIdInput(workId);
  }, [workId]);

  useEffect(() => {
    if (workId.trim()) persistWorkId(workId);
  }, [workId]);

  function applyWorkId(e) {
    e.preventDefault();
    const next = workIdInput.trim();
    const ws = (searchParams.get("workspace_id") || trace.workspaceId || "").trim();
    const p = new URLSearchParams();
    if (next) {
      persistWorkId(next);
      p.set("work_id", next);
    }
    if (ws) p.set("workspace_id", ws);
    if (searchParams.get("dev") === "1") p.set("dev", "1");
    setSearchParams(p);
  }

  const traceExtras = useMemo(
    () => ({
      chunkFingerprint: trace.chunkFingerprint,
      section: trace.section,
      citation: trace.citation,
      ...(effectiveWorkspaceId ? { workspaceId: effectiveWorkspaceId } : {}),
    }),
    [trace.chunkFingerprint, trace.section, trace.citation, effectiveWorkspaceId],
  );

  return (
    <Box sx={{ p: 2, ...mainShellContentSx, maxWidth: "100%" }}>
      <PageHeader eyebrow={t("evidence.header.eyebrow")} title={t("evidence.header.title")} description={t("evidence.header.description")} />

      {!workId.trim() ? (
        <Box
          sx={{
            p: 2,
            borderRadius: "6px",
            border: "1px dashed rgba(255,255,255,0.12)",
            backgroundColor: "rgba(255,255,255,0.02)",
            mb: 2,
          }}
        >
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)" }}>
            {t("evidence.empty.title")}
          </Typography>
          <Typography sx={{ mt: 0.75, fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)" }}>{t("evidence.empty.body")}</Typography>
          <Box sx={{ mt: 1.5, display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
            <CursorIconAction component={Link} to="/workspaces" title={t("readerShell.openWorkspaces")}>
              <FolderOpenOutlinedIcon sx={{ fontSize: "1.15rem" }} />
            </CursorIconAction>
            <CursorIconAction component={Link} to={getLastWorkspaceHref()} title={t("evidence.openLastWorkspace")}>
              <HubOutlinedIcon sx={{ fontSize: "1.15rem" }} />
            </CursorIconAction>
          </Box>
        </Box>
      ) : null}

      {workId.trim() ? (
        <Box sx={{ mb: 1.5, display: "flex", flexWrap: "wrap", gap: 0.75 }}>
          <CursorIconAction
            component={Link}
            to={buildWorkspaceTracePath(workId, "reader", traceExtras)}
            title={t("reader.openReaderWs")}
          >
            <MenuBookOutlinedIcon sx={{ fontSize: "1.1rem" }} />
          </CursorIconAction>
          <CursorIconAction
            component={Link}
            to={buildWorkspaceTracePath(workId, "graph", traceExtras)}
            title={t("reader.openGraphWs")}
          >
            <AccountTreeOutlinedIcon sx={{ fontSize: "1.1rem" }} />
          </CursorIconAction>
        </Box>
      ) : null}

      {workId.trim() ? (
        <EvidenceWorkBody
          workId={workId}
          workspaceId={trace.workspaceId}
          highlightedFingerprint={trace.chunkFingerprint}
          highlightedSection={trace.section}
          citation={trace.citation}
        />
      ) : null}

      {showDevWorkIdForm ? (
        <Accordion
          disableGutters
          elevation={0}
          sx={{
            mt: 2,
            borderRadius: "6px",
            border: "1px solid rgba(255,255,255,0.1)",
            backgroundColor: "rgba(255,255,255,0.02)",
            "&:before": { display: "none" },
          }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ color: "rgba(255,255,255,0.5)", fontSize: "1.1rem" }} />}>
            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)" }}>
              {t("evidence.devAdvancedTitle")}
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ pt: 0 }}>
            <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.42)", mb: 1.5 }}>{t("evidence.devAdvancedHint")}</Typography>
            <Box component="form" onSubmit={applyWorkId} sx={{ display: "flex", gap: 1, flexWrap: "wrap", alignItems: "flex-start" }}>
              <TextField
                label={t("reader.workIdLabel")}
                value={workIdInput}
                onChange={(ev) => setWorkIdInput(ev.target.value)}
                size="small"
                fullWidth
                sx={{
                  maxWidth: 480,
                  "& .MuiInputBase-input": { fontSize: "0.8125rem" },
                  "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
                }}
              />
              <CursorIconAction type="submit" title={t("reader.load")}>
                <PlayArrowOutlinedIcon sx={{ fontSize: "1.15rem" }} />
              </CursorIconAction>
            </Box>
          </AccordionDetails>
        </Accordion>
      ) : null}
    </Box>
  );
}
