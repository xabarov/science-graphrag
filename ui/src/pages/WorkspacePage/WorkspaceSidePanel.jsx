import React, { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";

import WorkspaceIngestPanel from "./WorkspaceIngestPanel.jsx";
import { useI18n } from "../../i18n/I18nContext.jsx";
import { getWorkspaceSmartDedupConflicts } from "../../utils/workspaceStore.js";

/**
 * Sticky right column: upload + graph snapshot + smart-dedup summary (links to main section).
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
 *   sideDedupRefresh?: number,
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
  sideDedupRefresh = 0,
}) {
  const { t } = useI18n();
  const [pendingConflicts, setPendingConflicts] = useState(null);

  const loadPendingCount = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const data = await getWorkspaceSmartDedupConflicts(workspaceId, { status: "pending", limit: 200 });
      const items = Array.isArray(data?.items) ? data.items : [];
      setPendingConflicts(items.length);
    } catch {
      setPendingConflicts(null);
    }
  }, [workspaceId]);

  useEffect(() => {
    const id = setTimeout(() => {
      void loadPendingCount();
    }, 0);
    return () => clearTimeout(id);
  }, [loadPendingCount, sideDedupRefresh]);

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

      <Box
        sx={{
          mt: 2,
          p: 1.25,
          borderRadius: "6px",
          border: "1px solid rgba(255,255,255,0.08)",
          backgroundColor: "rgba(255,255,255,0.02)",
        }}
      >
        <Typography sx={{ fontSize: "0.75rem", fontWeight: 600, color: "rgba(129,140,248,0.95)", mb: 0.5 }}>
          {t("workspace.side.dedupTitle")}
        </Typography>
        <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.5)", mb: 1, lineHeight: 1.45 }}>
          {pendingConflicts != null
            ? t("workspace.side.dedupPendingLine", { count: String(pendingConflicts) })
            : t("workspace.side.dedupPendingUnknown")}
        </Typography>
        <Link href="#workspace-dedup-section" underline="hover" sx={{ fontSize: "0.72rem", color: "rgba(129,140,248,0.95)" }}>
          {t("workspace.side.dedupJump")}
        </Link>
      </Box>
    </>
  );
}
