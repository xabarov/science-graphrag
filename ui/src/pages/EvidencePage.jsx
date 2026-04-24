import React, { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";

import { CursorPrimaryButton, CursorSmallButton } from "../components/common/index.js";
import PageHeader from "../components/layout/PageHeader.jsx";
import { useWorkspaceContext } from "../components/layout/WorkspaceContext.jsx";
import { mainShellContentSx } from "../components/layout/mainShellContentSx.js";
import { useI18n } from "../i18n/I18nContext.jsx";
import EvidenceWorkBody from "../components/work/EvidenceWorkBody.jsx";
import { persistWorkId } from "./WorkspacePage/utils/workContext.js";
import { buildWorkspaceTracePath, readTraceabilityState } from "../components/work/traceabilityState.js";

export default function EvidencePage() {
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const initial = searchParams.get("work_id") || "";
  const [workIdInput, setWorkIdInput] = useState(initial);
  const { activeWorkspaceId, getLastWorkspaceHref } = useWorkspaceContext();

  const workId = searchParams.get("work_id") || "";
  const trace = readTraceabilityState(searchParams);
  const workspaceIdInUrl = (searchParams.get("workspace_id") || "").trim();
  const effectiveWorkspaceId = useMemo(
    () => workspaceIdInUrl || trace.workspaceId || (activeWorkspaceId || "").trim(),
    [workspaceIdInUrl, trace.workspaceId, activeWorkspaceId],
  );

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

  const showEmptyWorkspaceCta = !workId.trim() && !workspaceIdInUrl && !activeWorkspaceId;

  return (
    <Box sx={{ p: 2, ...mainShellContentSx }}>
      <PageHeader
        eyebrow={t("evidence.header.eyebrow")}
        title={t("evidence.header.title")}
        description={
          <>
            {t("evidence.header.descBefore")}{" "}
            <code style={{ color: "rgba(129,140,248,0.95)" }}>work_id</code>
            {t("evidence.header.descMid")}
          </>
        }
      />

      <Box component="form" onSubmit={applyWorkId} sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
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
        <CursorPrimaryButton type="submit">{t("reader.load")}</CursorPrimaryButton>
      </Box>

      {!workId.trim() ? (
        <Box
          sx={{
            p: 2,
            borderRadius: "6px",
            border: "1px dashed rgba(255,255,255,0.12)",
            backgroundColor: "rgba(255,255,255,0.02)",
          }}
        >
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)" }}>
            {t("evidence.empty.title")}
          </Typography>
          <Typography sx={{ mt: 0.75, fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)" }}>{t("evidence.empty.body")}</Typography>
          {showEmptyWorkspaceCta ? (
            <Box sx={{ mt: 1.5 }}>
              <CursorPrimaryButton component={Link} to={getLastWorkspaceHref()} sx={{ textDecoration: "none" }}>
                {t("evidence.openLastWorkspace")}
              </CursorPrimaryButton>
            </Box>
          ) : null}
        </Box>
      ) : null}
      {workId.trim() ? (
        <Box sx={{ mb: 1.5, display: "flex", flexWrap: "wrap", gap: 1 }}>
          <CursorSmallButton
            component={Link}
            to={buildWorkspaceTracePath(workId, "reader", traceExtras)}
            sx={{ textDecoration: "none" }}
          >
            {t("reader.openReaderWs")}
          </CursorSmallButton>
          <CursorSmallButton component={Link} to={buildWorkspaceTracePath(workId, "graph", traceExtras)} sx={{ textDecoration: "none" }}>
            {t("reader.openGraphWs")}
          </CursorSmallButton>
        </Box>
      ) : null}

      {workId.trim() ? (
        <EvidenceWorkBody
          workId={workId}
          highlightedFingerprint={trace.chunkFingerprint}
          highlightedSection={trace.section}
          citation={trace.citation}
        />
      ) : null}
    </Box>
  );
}
