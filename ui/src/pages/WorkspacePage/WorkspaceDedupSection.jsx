import React, { useCallback, useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { CursorButton, CursorSmallButton } from "../../components/common/index.js";

import DeduplicationPanel from "../../components/graph/DeduplicationPanel.jsx";
import WorkDedupReviewDialog from "../../components/graph/dedup/WorkDedupReviewDialog.jsx";
import { formatResearchApiError } from "../../services/researchApi.js";
import {
  getWorkspaceDedupJob,
  getWorkspaceSmartDedupConflicts,
  startWorkspaceSmartDedupScan,
} from "../../utils/workspaceStore.js";
import usePollJob from "../../hooks/usePollJob.js";

/**
 * @param {{ workspaceId: string, onMerged: () => void }} props
 */
export default function WorkspaceDedupSection({ workspaceId, onMerged }) {
  const [scanBusy, setScanBusy] = useState(false);
  const [scanMsg, setScanMsg] = useState(null);
  const [conflicts, setConflicts] = useState([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [activeConflict, setActiveConflict] = useState(null);
  const [dedupJobId, setDedupJobId] = useState("");

  const loadConflicts = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const data = await getWorkspaceSmartDedupConflicts(workspaceId, { status: "pending", limit: 40 });
      setConflicts(Array.isArray(data?.items) ? data.items : []);
    } catch {
      setConflicts([]);
    }
  }, [workspaceId]);

  useEffect(() => {
    const id = setTimeout(() => {
      void loadConflicts();
    }, 0);
    return () => clearTimeout(id);
  }, [loadConflicts]);

  usePollJob({
    enabled: Boolean(dedupJobId),
    intervalMs: 1000,
    fetchJob: useCallback(() => getWorkspaceDedupJob(workspaceId, dedupJobId), [workspaceId, dedupJobId]),
    onTerminal: useCallback(
      async (done) => {
        if (done?.status === "failed") {
          setScanMsg(formatResearchApiError({ message: done?.error || done?.message || "scan_failed" }));
        } else {
          setScanMsg(
            `Scan done: ${String(done?.conflicts_inserted ?? done?.message ?? "")} new conflict(s). Refresh list below.`,
          );
          await loadConflicts();
        }
        setScanBusy(false);
        setDedupJobId("");
      },
      [loadConflicts],
    ),
    onError: useCallback((err, failCount) => {
      if (failCount >= 3) {
        setScanMsg(formatResearchApiError(err));
        setScanBusy(false);
        setDedupJobId("");
      }
    }, []),
  });

  const onScan = async () => {
    if (!workspaceId) return;
    setScanBusy(true);
    setScanMsg(null);
    try {
      const start = await startWorkspaceSmartDedupScan(workspaceId);
      const jid = start?.job_id;
      if (!jid) {
        setScanMsg("No job_id returned");
        setScanBusy(false);
        return;
      }
      setDedupJobId(String(jid));
    } catch (e) {
      setScanMsg(formatResearchApiError(e));
      setScanBusy(false);
    }
  };

  if (!workspaceId) return null;

  return (
    <Box sx={{ mt: 2.5 }}>
      <Typography sx={{ fontSize: "0.8125rem", fontWeight: 600, mb: 1, color: "rgba(129,140,248,0.95)" }}>
        Smart dedup (embeddings + LLM)
      </Typography>
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 1.5 }}>
        Scans work summary vectors in this workspace and opens a review queue. Requires ingested papers (work
        embeddings). Key-only duplicates remain under the classic panel below.
      </Typography>
      <CursorButton variant="outlined" size="small" onClick={() => void onScan()} disabled={scanBusy} sx={{ mb: 1 }}>
        {scanBusy ? "Scanning…" : "Scan for near-duplicates"}
      </CursorButton>
      {scanMsg ? (
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)", mb: 1 }}>{scanMsg}</Typography>
      ) : null}
      {conflicts.length === 0 ? (
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mb: 2 }}>
          No pending smart-dedup conflicts.
        </Typography>
      ) : (
        <Box sx={{ mb: 2 }}>
          <Typography sx={{ fontSize: "0.75rem", mb: 1 }}>
            Pending: <strong>{conflicts.length}</strong>
          </Typography>
          {conflicts.slice(0, 8).map((c) => (
            <Box
              key={String(c.id)}
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                py: 0.75,
                borderBottom: "1px solid rgba(255,255,255,0.06)",
              }}
            >
              <Typography sx={{ fontSize: "0.72rem", fontFamily: "ui-monospace, monospace" }}>
                {String(c.work_id_a).slice(0, 10)}… ↔ {String(c.work_id_b).slice(0, 10)}… · sim{" "}
                {Number(c.similarity_score).toFixed(3)}
              </Typography>
              <CursorSmallButton
                onClick={() => {
                  setActiveConflict(c);
                  setDialogOpen(true);
                }}
              >
                Review
              </CursorSmallButton>
            </Box>
          ))}
        </Box>
      )}
      <WorkDedupReviewDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        workspaceId={workspaceId}
        conflict={activeConflict}
        onDecided={() => {
          void loadConflicts();
          onMerged();
        }}
      />
      <DeduplicationPanel workspaceId={workspaceId} onMerged={onMerged} />
    </Box>
  );
}
