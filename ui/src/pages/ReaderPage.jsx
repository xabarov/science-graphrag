import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";

import { CursorPrimaryButton, CursorSmallButton } from "../components/common/index.js";
import PageHeader from "../components/layout/PageHeader.jsx";
import { mainShellContentSx } from "../components/layout/mainShellContentSx.js";
import { useI18n } from "../i18n/I18nContext.jsx";
import ReaderWorkBody from "../components/work/ReaderWorkBody.jsx";
import { persistWorkId } from "./WorkspacePage/utils/workContext.js";
import { buildWorkspaceTracePath, readTraceabilityState } from "../components/work/traceabilityState.js";

export default function ReaderPage() {
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const initial = searchParams.get("work_id") || "";
  const [workIdInput, setWorkIdInput] = useState(initial);

  const workId = searchParams.get("work_id") || "";
  const trace = readTraceabilityState(searchParams);

  useEffect(() => {
    setWorkIdInput(workId);
  }, [workId]);

  useEffect(() => {
    if (workId.trim()) persistWorkId(workId);
  }, [workId]);

  function applyWorkId(e) {
    e.preventDefault();
    const next = workIdInput.trim();
    if (next) {
      persistWorkId(next);
      setSearchParams({ work_id: next });
    } else setSearchParams({});
  }

  return (
    <Box sx={{ p: 2, ...mainShellContentSx }}>
      <PageHeader
        eyebrow={t("reader.header.eyebrow")}
        title={t("reader.header.title")}
        description={
          <>
            {t("reader.header.descBefore")}{" "}
            <code style={{ color: "rgba(129,140,248,0.95)" }}>work_id</code>
            {t("reader.header.descAfter")}
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
            {t("reader.empty.title")}
          </Typography>
          <Typography sx={{ mt: 0.75, fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)" }}>{t("reader.empty.body")}</Typography>
        </Box>
      ) : null}
      {workId.trim() ? (
        <ReaderWorkBody
          workId={workId}
          focusedFingerprint={trace.chunkFingerprint}
          focusedSection={trace.section}
          citation={trace.citation}
        />
      ) : null}
      {workId.trim() ? (
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
