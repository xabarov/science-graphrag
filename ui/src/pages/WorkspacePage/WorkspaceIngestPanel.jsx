import React, { useCallback, useState } from "react";
import FolderZipOutlinedIcon from "@mui/icons-material/FolderZipOutlined";
import LibraryAddOutlinedIcon from "@mui/icons-material/LibraryAddOutlined";
import UploadFileOutlinedIcon from "@mui/icons-material/UploadFileOutlined";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import { CursorIconButton, CursorSmallButton } from "../../components/common/index.js";
import IngestProgressCard from "../../components/ingestion/IngestProgressCard.jsx";
import { useI18n } from "../../i18n/useI18n.js";
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
 *   variant?: "default" | "popover",
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
  variant = "default",
}) {
  const { t } = useI18n();
  const [dragOver, setDragOver] = useState(false);
  const compact = variant === "popover";

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
  const disabledPick = uploadBusy || Boolean(ingestJobId);

  return (
    <>
      <Box
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        sx={{
          mb: compact ? 1.25 : 2,
          p: compact ? 1 : 1.5,
          borderRadius: "6px",
          border: dragOver ? "1px dashed rgba(129,140,248,0.65)" : "1px solid rgba(255,255,255,0.1)",
          backgroundColor: dragOver ? "rgba(99,102,241,0.08)" : "rgba(255,255,255,0.02)",
        }}
      >
        <Typography sx={{ fontSize: "0.68rem", fontWeight: 600, color: "rgba(255,255,255,0.45)", mb: 0.75 }}>
          {t("workspace.upload.title")}
        </Typography>
        <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.45)", mb: 1, lineHeight: 1.45 }}>
          {t("workspace.upload.desc")}
        </Typography>
        <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.35)", mb: 1 }}>
          {t("workspace.upload.dropHint")}
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
          <input type="file" accept=".pdf,.md,.txt" hidden id="workspace-ingest-input" onChange={(e) => onUploadDocument(e)} />
          <Tooltip title={uploadBusy ? t("workspace.upload.starting") : ingestJobId ? t("workspace.upload.processing") : t("workspace.upload.chooseFile")}>
            <span>
              <label htmlFor="workspace-ingest-input">
                <CursorIconButton component="span" disabled={disabledPick} sx={{ cursor: disabledPick ? "default" : "pointer" }}>
                  <UploadFileOutlinedIcon sx={{ fontSize: "1.1rem" }} />
                </CursorIconButton>
              </label>
            </span>
          </Tooltip>
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
              <Tooltip title={t("workspace.upload.chooseMultiple")}>
                <span>
                  <label htmlFor="workspace-ingest-multi">
                    <CursorIconButton component="span" disabled={disabledPick} sx={{ cursor: disabledPick ? "default" : "pointer" }}>
                      <LibraryAddOutlinedIcon sx={{ fontSize: "1.1rem" }} />
                    </CursorIconButton>
                  </label>
                </span>
              </Tooltip>
              <input type="file" accept=".zip" hidden id="workspace-ingest-zip" onChange={(e) => void onZipInputChange(e)} />
              <Tooltip title={t("workspace.upload.chooseZip")}>
                <span>
                  <label htmlFor="workspace-ingest-zip">
                    <CursorIconButton component="span" disabled={disabledPick} sx={{ cursor: disabledPick ? "default" : "pointer" }}>
                      <FolderZipOutlinedIcon sx={{ fontSize: "1.1rem" }} />
                    </CursorIconButton>
                  </label>
                </span>
              </Tooltip>
            </>
          ) : null}
        </Box>
        {ingestErr ? (
          <Alert severity="warning" sx={{ mt: 1.25, fontSize: "0.75rem" }}>
            {ingestErr}
          </Alert>
        ) : null}
        {ingestJob ? (
          isParentBatch ? (
            <Box sx={{ mt: 1.5 }}>
              <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.5)", fontFamily: "monospace" }}>
                {t("workspace.upload.jobLine", { id: String(ingestJob.job_id), status: String(ingestJob.status) })}
              </Typography>
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)", mt: 0.5 }}>
                {ingestJob.message || t("workspace.upload.dash")}
              </Typography>
              {childJobs.length ? (
                <Box sx={{ mt: 1, display: "flex", flexDirection: "column", gap: 1 }}>
                  {childJobs.map((cj) => {
                    const pctFromBackend =
                      typeof cj.progress_pct === "number" && Number.isFinite(cj.progress_pct)
                        ? Math.min(100, Math.max(0, cj.progress_pct * 100))
                        : null;
                    const pct =
                      pctFromBackend != null
                        ? pctFromBackend
                        : Math.min(
                            100,
                            Math.max(
                              0,
                              (Number(cj.progress_total) || 0) > 0
                                ? (100 * (Number(cj.progress_current) || 0)) / Number(cj.progress_total)
                                : Number(cj.progress_current) || 0,
                            ),
                          );
                    return (
                      <Box key={String(cj.job_id)}>
                        <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.5)", mb: 0.35 }}>
                          {String(cj.filename || t("workspace.upload.dash"))} · {String(cj.status || "—")}
                        </Typography>
                        <LinearProgress
                          variant="determinate"
                          value={pct}
                          sx={{
                            height: 3,
                            borderRadius: 2,
                            backgroundColor: "rgba(255,255,255,0.06)",
                            "& .MuiLinearProgress-bar": { backgroundColor: "rgba(99,102,241,0.75)" },
                          }}
                        />
                      </Box>
                    );
                  })}
                </Box>
              ) : null}
              {ingestJob.logs ? (
                <Accordion
                  defaultExpanded={false}
                  disableGutters
                  sx={{
                    mt: 1,
                    backgroundColor: "#141414",
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: "6px",
                    "&:before": { display: "none" },
                  }}
                >
                  <AccordionSummary sx={{ fontSize: "0.72rem", minHeight: 32 }}>
                    {t("workspace.ingest.detailsLogs")}
                  </AccordionSummary>
                  <AccordionDetails sx={{ pt: 0 }}>
                    <Typography sx={{ fontSize: "0.65rem", color: "rgba(255,255,255,0.38)", mb: 0.75 }}>
                      {t("workspace.ingest.logsTailHint")}
                    </Typography>
                    <Box
                      component="pre"
                      sx={{
                        maxHeight: 140,
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
                  </AccordionDetails>
                </Accordion>
              ) : null}
            </Box>
          ) : (
            <IngestProgressCard ingestJob={ingestJob} />
          )
        ) : null}
      </Box>

      <Accordion
        defaultExpanded={false}
        disableGutters
        sx={{
          mb: compact ? 0 : 2,
          maxWidth: compact ? "none" : 560,
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
                minWidth: 200,
                flex: "1 1 180px",
                "& .MuiInputBase-input": { fontSize: "0.8125rem" },
                "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
              }}
            />
            <CursorSmallButton type="submit" disabled={addBusy || !addWorkInput.trim()}>
              {t("workspace.advanced.add")}
            </CursorSmallButton>
          </Box>
        </AccordionDetails>
      </Accordion>
    </>
  );
}
