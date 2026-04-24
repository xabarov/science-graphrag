import React, { useCallback, useState } from "react";
import Box from "@mui/material/Box";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Alert from "@mui/material/Alert";
import LinearProgress from "@mui/material/LinearProgress";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { CursorPrimaryButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/I18nContext.jsx";
import { collectIngestFilesFromDataTransfer } from "./collectIngestFiles.js";

/**
 * @param {{
 *   workspaceId: string,
 *   uploadBusy: boolean,
 *   ingestJobId: string,
 *   ingestJob: object | null,
 *   ingestErr: string | null,
 *   onUploadDocument: (ev: React.ChangeEvent<HTMLInputElement>) => void,
 *   onUploadBatch?: (files: File[], archive: File | null) => void | Promise<void>,
 *   addWorkInput: string,
 *   onAddWorkInputChange: (v: string) => void,
 *   addBusy: boolean,
 *   onAddWork: (e?: React.FormEvent) => void | Promise<void>,
 * }} props
 */
export default function WorkspaceIngestPanel({
  workspaceId,
  uploadBusy,
  ingestJobId,
  ingestJob,
  ingestErr,
  onUploadDocument,
  onUploadBatch,
  addWorkInput,
  onAddWorkInputChange,
  addBusy,
  onAddWork,
}) {
  const { t } = useI18n();
  const [dragOver, setDragOver] = useState(false);

  const onDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  }, []);

  const onDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  }, []);

  const onDrop = useCallback(
    async (e) => {
      e.preventDefault();
      e.stopPropagation();
      setDragOver(false);
      if (!onUploadBatch || uploadBusy || Boolean(ingestJobId)) return;
      const files = await collectIngestFilesFromDataTransfer(e.dataTransfer);
      if (files.length) await onUploadBatch(files, null);
    },
    [onUploadBatch, uploadBusy, ingestJobId],
  );

  async function onMultiInputChange(ev) {
    const fl = ev.target.files;
    ev.target.value = "";
    if (!fl?.length || !onUploadBatch) return;
    await onUploadBatch(Array.from(fl), null);
  }

  async function onZipInputChange(ev) {
    const f = ev.target.files?.[0];
    ev.target.value = "";
    if (!f || !onUploadBatch) return;
    await onUploadBatch([], f);
  }

  if (!workspaceId) return null;

  const isParentBatch = String(ingestJob?.kind || "") === "batch_parent";
  const childJobs = Array.isArray(ingestJob?.child_jobs) ? ingestJob.child_jobs : [];

  return (
    <>
      <Box
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        sx={{
          mb: 2,
          p: 1.5,
          borderRadius: "6px",
          border: dragOver ? "1px dashed rgba(129,140,248,0.75)" : "1px solid rgba(99,102,241,0.22)",
          backgroundColor: dragOver ? "rgba(99,102,241,0.12)" : "rgba(99,102,241,0.06)",
          maxWidth: 560,
        }}
      >
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)", mb: 1 }}>{t("workspace.upload.title")}</Typography>
        <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.45)", mb: 1.25, lineHeight: 1.45 }}>
          {t("workspace.upload.desc")}
        </Typography>
        <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.38)", mb: 1 }}>
          {t("workspace.upload.dropHint")}
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
          <input type="file" accept=".pdf,.md,.txt" hidden id="workspace-ingest-input" onChange={(e) => onUploadDocument(e)} />
          <label htmlFor="workspace-ingest-input">
            <CursorPrimaryButton component="span" disabled={uploadBusy || Boolean(ingestJobId)} sx={{ cursor: "pointer" }}>
              {uploadBusy ? t("workspace.upload.starting") : ingestJobId ? t("workspace.upload.processing") : t("workspace.upload.chooseFile")}
            </CursorPrimaryButton>
          </label>
          {onUploadBatch ? (
            <>
              <input
                type="file"
                multiple
                accept=".pdf,.md,.txt"
                hidden
                id="workspace-ingest-multi"
                onChange={(e) => void onMultiInputChange(e)}
              />
              <label htmlFor="workspace-ingest-multi">
                <CursorPrimaryButton component="span" disabled={uploadBusy || Boolean(ingestJobId)} sx={{ cursor: "pointer" }}>
                  {t("workspace.upload.chooseMultiple")}
                </CursorPrimaryButton>
              </label>
              <input type="file" accept=".zip" hidden id="workspace-ingest-zip" onChange={(e) => void onZipInputChange(e)} />
              <label htmlFor="workspace-ingest-zip">
                <CursorPrimaryButton component="span" disabled={uploadBusy || Boolean(ingestJobId)} sx={{ cursor: "pointer" }}>
                  {t("workspace.upload.chooseZip")}
                </CursorPrimaryButton>
              </label>
            </>
          ) : null}
        </Box>
        {ingestErr ? (
          <Alert severity="warning" sx={{ mt: 1.25, fontSize: "0.75rem" }}>
            {ingestErr}
          </Alert>
        ) : null}
        {ingestJob ? (
          <Box sx={{ mt: 1.5 }}>
            <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.5)", fontFamily: "monospace" }}>
              {t("workspace.upload.jobLine", { id: String(ingestJob.job_id), status: String(ingestJob.status) })}
            </Typography>
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)", mt: 0.5 }}>
              {ingestJob.message || t("workspace.upload.dash")}
            </Typography>
            <LinearProgress
              variant="determinate"
              value={Math.min(100, Math.max(0, Number(ingestJob.progress_current) || 0))}
              sx={{
                mt: 1,
                height: 4,
                borderRadius: 2,
                backgroundColor: "rgba(255,255,255,0.06)",
                "& .MuiLinearProgress-bar": { backgroundColor: "rgba(129,140,248,0.85)" },
              }}
            />
            {!isParentBatch && ingestJob.work_id ? (
              <Typography sx={{ fontSize: "0.72rem", color: "rgba(129,140,248,0.9)", mt: 0.75 }}>
                {t("workspace.upload.newWorkId")} <code>{ingestJob.work_id}</code>
              </Typography>
            ) : null}
            {isParentBatch && childJobs.length ? (
              <Box sx={{ mt: 1, display: "flex", flexDirection: "column", gap: 0.5 }}>
                {childJobs.map((cj) => (
                  <Typography key={String(cj.job_id)} sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.5)" }}>
                    {String(cj.filename || "—")} · {String(cj.status || "—")}
                  </Typography>
                ))}
              </Box>
            ) : null}
            {ingestJob.logs ? (
              <Box
                component="pre"
                sx={{
                  mt: 1,
                  maxHeight: 120,
                  overflow: "auto",
                  fontSize: "0.65rem",
                  color: "rgba(255,255,255,0.45)",
                  backgroundColor: "#0a0a0a",
                  p: 1,
                  borderRadius: "4px",
                  border: "1px solid rgba(255,255,255,0.08)",
                }}
              >
                {ingestJob.logs}
              </Box>
            ) : null}
          </Box>
        ) : null}
      </Box>

      <Accordion
        defaultExpanded={false}
        disableGutters
        sx={{
          mb: 2,
          maxWidth: 560,
          backgroundColor: "#141414",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: "6px",
          "&:before": { display: "none" },
        }}
      >
        <AccordionSummary sx={{ fontSize: "0.8125rem", fontWeight: 600 }}>{t("workspace.advanced.accordion")}</AccordionSummary>
        <AccordionDetails sx={{ pt: 0 }}>
          <Box component="form" onSubmit={onAddWork} sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "flex-start" }}>
            <TextField
              label={t("workspace.advanced.workIdLabel")}
              value={addWorkInput}
              onChange={(ev) => onAddWorkInputChange(ev.target.value)}
              size="small"
              placeholder={t("workspace.advanced.placeholder")}
              sx={{
                minWidth: 220,
                flex: "1 1 200px",
                "& .MuiInputBase-input": { fontSize: "0.8125rem" },
                "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
              }}
            />
            <CursorPrimaryButton type="submit" disabled={addBusy || !addWorkInput.trim()}>
              {t("workspace.advanced.add")}
            </CursorPrimaryButton>
          </Box>
        </AccordionDetails>
      </Accordion>
    </>
  );
}
