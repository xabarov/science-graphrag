import React, { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import { CursorPrimaryButton, CursorSmallButton } from "../components/common/index.js";
import PageHeader from "../components/layout/PageHeader.jsx";
import { mainShellContentSx } from "../components/layout/mainShellContentSx.js";
import { useI18n } from "../i18n/I18nContext.jsx";
import ReaderWorkBody from "../components/work/ReaderWorkBody.jsx";
import { getLastWorkId, persistWorkId } from "./WorkspacePage/utils/workContext.js";
import { buildWorkspaceTracePath, readTraceabilityState } from "../components/work/traceabilityState.js";

export default function ReaderPage() {
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const initial = searchParams.get("work_id") || "";
  const [workIdInput, setWorkIdInput] = useState(initial);
  const [workMeta, setWorkMeta] = useState({ title: "", loading: false, error: "" });

  const workId = searchParams.get("work_id") || "";
  const trace = readTraceabilityState(searchParams);

  useEffect(() => {
    setWorkIdInput(workId);
  }, [workId]);

  useEffect(() => {
    if (!workId.trim()) {
      setWorkMeta({ title: "", loading: false, error: "" });
    }
  }, [workId]);

  useEffect(() => {
    if (workId.trim()) persistWorkId(workId);
  }, [workId]);

  const handleWorkMetaChange = useCallback((meta) => {
    setWorkMeta(meta);
  }, []);

  function applyWorkId(e) {
    e.preventDefault();
    const next = workIdInput.trim();
    if (next) {
      persistWorkId(next);
      setSearchParams({ work_id: next });
    } else setSearchParams({});
  }

  function openLastArticle() {
    const id = getLastWorkId();
    if (!id) return;
    persistWorkId(id);
    setSearchParams({ work_id: id });
  }

  const lastId = getLastWorkId();
  const hasWork = Boolean(workId.trim());

  const pageEyebrow = hasWork ? t("readerShell.articleEyebrow") : t("reader.header.eyebrow");
  const pageTitle = !hasWork
    ? t("readerShell.heroEmptyTitle")
    : workMeta.loading
      ? t("readerShell.loadingTitle")
      : workMeta.title.trim()
        ? workMeta.title
        : t("readerBody.noTitle");

  const pageDescription = !hasWork ? (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
      <span>{t("readerShell.heroEmptyDesc")}</span>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
        <CursorPrimaryButton component={Link} to="/workspaces" sx={{ textDecoration: "none" }}>
          {t("readerShell.openWorkspaces")}
        </CursorPrimaryButton>
        {lastId ? (
          <CursorSmallButton type="button" onClick={openLastArticle}>
            {t("readerShell.openLastArticle")}
          </CursorSmallButton>
        ) : null}
      </Box>
    </Box>
  ) : workMeta.error ? (
    workMeta.error
  ) : (
    ""
  );

  return (
    <Box sx={{ p: 2, ...mainShellContentSx }}>
      <PageHeader eyebrow={pageEyebrow} title={pageTitle} description={pageDescription} />

      <Accordion
        disableGutters
        elevation={0}
        sx={{
          mb: 2,
          borderRadius: "6px",
          border: "1px solid rgba(255,255,255,0.1)",
          backgroundColor: "rgba(255,255,255,0.02)",
          "&:before": { display: "none" },
        }}
      >
        <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ color: "rgba(255,255,255,0.5)", fontSize: "1.1rem" }} />}>
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)" }}>
            {t("readerShell.advancedTitle")}
          </Typography>
        </AccordionSummary>
        <AccordionDetails sx={{ pt: 0 }}>
          <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.42)", mb: 1.5 }}>{t("readerShell.advancedHint")}</Typography>
          <Box component="form" onSubmit={applyWorkId} sx={{ display: "flex", gap: 1, flexWrap: "wrap", alignItems: "flex-start" }}>
            <TextField
              label={t("readerShell.workIdLabel")}
              value={workIdInput}
              onChange={(ev) => setWorkIdInput(ev.target.value)}
              size="small"
              sx={{
                flex: "1 1 280px",
                maxWidth: 520,
                "& .MuiInputBase-input": { fontSize: "0.8125rem" },
                "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
              }}
            />
            <CursorPrimaryButton type="submit">{t("readerShell.load")}</CursorPrimaryButton>
          </Box>
        </AccordionDetails>
      </Accordion>

      {!hasWork ? null : (
        <ReaderWorkBody
          workId={workId}
          focusedFingerprint={trace.chunkFingerprint}
          focusedSection={trace.section}
          citation={trace.citation}
          layoutVariant="readerPage"
          onWorkMetaChange={handleWorkMetaChange}
        />
      )}

      {hasWork ? (
        <Box sx={{ mt: 1.5, display: "flex", flexWrap: "wrap", gap: 1 }}>
          <CursorSmallButton
            component={Link}
            to={buildWorkspaceTracePath(workId, "reader", {
              chunkFingerprint: trace.chunkFingerprint,
              section: trace.section,
              citation: trace.citation,
            })}
            sx={{ textDecoration: "none" }}
          >
            {t("reader.openReaderWs")}
          </CursorSmallButton>
          <CursorSmallButton
            component={Link}
            to={buildWorkspaceTracePath(workId, "graph", {
              section: trace.section,
              citation: trace.citation,
            })}
            sx={{ textDecoration: "none" }}
          >
            {t("reader.openGraphWs")}
          </CursorSmallButton>
        </Box>
      ) : null}
    </Box>
  );
}
