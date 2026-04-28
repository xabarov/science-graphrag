import React, { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import AccountTreeIcon from "@mui/icons-material/AccountTree";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import FolderOpenIcon from "@mui/icons-material/FolderOpen";
import HistoryIcon from "@mui/icons-material/History";
import MenuBookIcon from "@mui/icons-material/MenuBook";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";

import { CursorIconAction } from "../components/common/index.js";
import { isExplicitAdminMode } from "../components/layout/adminVisibility.js";
import PageHeader from "../components/layout/PageHeader.jsx";
import { useI18n } from "../i18n/useI18n.js";
import ReaderWorkBody from "../components/work/reader/ReaderWorkBody.jsx";
import { getLastWorkId, persistWorkId } from "./WorkspacePage/utils/workContext.js";
import { GRAPH_PATH, READER_PATH } from "../routes/paths.js";
import {
  buildStandaloneTracePath,
  readTraceabilityState,
} from "../components/work/traceability/traceabilityState.js";

export default function ReaderPage() {
  const theme = useTheme();
  const tk = theme.appTokens;
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const initial = searchParams.get("work_id") || "";
  const [workIdInput, setWorkIdInput] = useState(initial);
  const [workMeta, setWorkMeta] = useState({ title: "", loading: false, error: "" });

  const workId = searchParams.get("work_id") || "";
  const trace = readTraceabilityState(searchParams);
  const showDevWorkIdAccordion = searchParams.get("dev") === "1" || isExplicitAdminMode();

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
    const p = new URLSearchParams();
    if (next) {
      persistWorkId(next);
      p.set("work_id", next);
    }
    if (searchParams.get("dev") === "1") p.set("dev", "1");
    setSearchParams(p);
  }

  function openLastArticle() {
    const id = getLastWorkId();
    if (!id) return;
    persistWorkId(id);
    const p = new URLSearchParams({ work_id: id });
    if (searchParams.get("dev") === "1") p.set("dev", "1");
    setSearchParams(p);
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
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
        <CursorIconAction component={Link} to="/workspaces" title={t("readerShell.openWorkspaces")}>
          <FolderOpenIcon sx={{ fontSize: "1.1rem" }} />
        </CursorIconAction>
        {lastId ? (
          <CursorIconAction type="button" title={t("readerShell.openLastArticle")} onClick={openLastArticle}>
            <HistoryIcon sx={{ fontSize: "1.1rem" }} />
          </CursorIconAction>
        ) : null}
      </Box>
    </Box>
  ) : workMeta.error ? (
    workMeta.error
  ) : (
    ""
  );

  return (
    <Box
      sx={{
        p: 2,
        width: "100%",
        maxWidth: "100%",
        minWidth: 0,
        boxSizing: "border-box",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <PageHeader eyebrow={pageEyebrow} title={pageTitle} description={pageDescription} />

      {hasWork ? (
        <Box
          sx={{
            mb: 1.5,
            display: "flex",
            flexWrap: "wrap",
            gap: 0.75,
            alignItems: "center",
            borderBottom: `1px solid ${tk.border.default}`,
            pb: 1.25,
          }}
        >
          <CursorIconAction
            component={Link}
            to={buildStandaloneTracePath(READER_PATH, workId, {
              chunkFingerprint: trace.chunkFingerprint,
              section: trace.section,
              citation: trace.citation,
            })}
            title={t("reader.openReaderWs")}
          >
            <MenuBookIcon sx={{ fontSize: "1.1rem" }} />
          </CursorIconAction>
          <CursorIconAction
            component={Link}
            to={buildStandaloneTracePath(GRAPH_PATH, workId, {
              section: trace.section,
              citation: trace.citation,
            })}
            title={t("reader.openGraphWs")}
          >
            <AccountTreeIcon sx={{ fontSize: "1.1rem" }} />
          </CursorIconAction>
        </Box>
      ) : null}

      {showDevWorkIdAccordion ? (
        <Accordion
          disableGutters
          elevation={0}
          sx={{
            mb: 2,
            borderRadius: "6px",
            border: `1px solid ${tk.border.default}`,
            backgroundColor: tk.surface.subtle,
            "&:before": { display: "none" },
          }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ color: tk.text.muted, fontSize: "1.1rem" }} />}>
            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: tk.text.primary }}>
              {t("readerShell.advancedTitle")}
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ pt: 0 }}>
            <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, mb: 1.5 }}>{t("readerShell.advancedHint")}</Typography>
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
                  "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: tk.text.secondary },
                }}
              />
              <CursorIconAction type="submit" title={t("readerShell.load")}>
                <PlayArrowIcon sx={{ fontSize: "1.15rem" }} />
              </CursorIconAction>
            </Box>
          </AccordionDetails>
        </Accordion>
      ) : null}

      {!hasWork ? null : (
        <Box sx={{ minWidth: 0, display: "flex", flexDirection: "column" }}>
          <ReaderWorkBody
            workId={workId}
            workspaceId={trace.workspaceId}
            focusedFingerprint={trace.chunkFingerprint}
            focusedSection={trace.section}
            citation={trace.citation}
            onWorkMetaChange={handleWorkMetaChange}
          />
        </Box>
      )}
    </Box>
  );
}
