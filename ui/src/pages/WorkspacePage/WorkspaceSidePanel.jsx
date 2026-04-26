import React from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import WorkspaceIngestPanel from "./WorkspaceIngestPanel.jsx";
import { useI18n } from "../../i18n/I18nContext.jsx";

/**
 * Sticky right column: upload + graph snapshot.
 * @param {{
 *   workspaceId: string,
 *   graphStats: Record<string, unknown> | null,
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
 *   addErr: string | null,
 * }} props
 */
export default function WorkspaceSidePanel({
  workspaceId,
  graphStats,
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
  addErr,
}) {
  const { t } = useI18n();

  if (!workspaceId) return null;

  return (
    <>
      <WorkspaceIngestPanel
        workspaceId={workspaceId}
        uploadBusy={uploadBusy}
        ingestJobId={ingestJobId}
        ingestJob={ingestJob}
        ingestErr={ingestErr}
        onUploadDocument={onUploadDocument}
        onUploadBatch={onUploadBatch}
        addWorkInput={addWorkInput}
        onAddWorkInputChange={onAddWorkInputChange}
        addBusy={addBusy}
        onAddWork={onAddWork}
      />
      {addErr ? (
        <Alert severity="warning" sx={{ mt: 1.5, fontSize: "0.8125rem" }}>
          {addErr}
        </Alert>
      ) : null}

      {graphStats && typeof graphStats === "object" ? (
        <Box
          sx={{
            mt: 2,
            p: 1.25,
            borderRadius: "6px",
            border: "1px solid rgba(255,255,255,0.08)",
            backgroundColor: "rgba(255,255,255,0.02)",
          }}
        >
          <Typography sx={{ fontSize: "0.75rem", fontWeight: 600, color: "rgba(129,140,248,0.95)", mb: 0.75 }}>
            {t("workspace.side.graphTitle")}
          </Typography>
          <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.55)", lineHeight: 1.45 }}>
            {t("workspace.side.graphStatsLine", {
              works: String(graphStats.works_count ?? "—"),
              authors: String(graphStats.authors_count ?? "—"),
              internal: String(graphStats.internal_citations ?? "—"),
              external: String(graphStats.external_citations ?? "—"),
            })}
          </Typography>
        </Box>
      ) : null}
    </>
  );
}
