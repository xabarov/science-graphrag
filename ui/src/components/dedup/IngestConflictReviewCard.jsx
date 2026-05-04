import React, { useCallback, useEffect, useState } from "react";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { getWorkDetail } from "../../services/research/works.js";
import { decideWorkspaceSmartDedupConflict, getWorkspaceSmartDedupConflicts } from "../../utils/workspaceStore.js";

/**
 * Review queue for work pairs created during ingest (origin=ingest).
 *
 * @param {{
 *   workspaceId: string,
 *   onDismiss: () => void,
 *   onMerged: () => void | Promise<void>,
 *   activeIngestJobId?: string,
 * }} props
 */
export default function IngestConflictReviewCard({ workspaceId, onDismiss, onMerged, activeIngestJobId = "" }) {
  const { t } = useI18n();
  const [items, setItems] = useState([]);
  const [idx, setIdx] = useState(0);
  const [titles, setTitles] = useState({});
  const [busy, setBusy] = useState(false);
  const [loadErr, setLoadErr] = useState("");

  const reload = useCallback(async () => {
    if (!workspaceId) return;
    setLoadErr("");
    try {
      const data = await getWorkspaceSmartDedupConflicts(workspaceId, {
        status: "pending",
        origin: "ingest",
        limit: 50,
      });
      const next = Array.isArray(data?.items) ? data.items : [];
      setItems(next);
      setIdx(0);
    } catch (e) {
      setLoadErr(String(e?.message || e || "load_failed"));
    }
  }, [workspaceId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    setIdx((i) => Math.min(i, Math.max(0, items.length - 1)));
  }, [items.length]);

  const safeIdx = items.length ? Math.min(idx, items.length - 1) : 0;
  const cur = items.length ? items[safeIdx] : null;

  useEffect(() => {
    if (!cur) return undefined;
    let cancelled = false;
    (async () => {
      const ids = [cur.work_id_a, cur.work_id_b].filter(Boolean);
      const fetched = {};
      for (const wid of ids) {
        try {
          const res = await getWorkDetail(wid);
          const row = res?.data;
          fetched[wid] = String(row?.title || wid).trim() || wid;
        } catch {
          fetched[wid] = wid;
        }
      }
      if (!cancelled) {
        setTitles((prev) => ({ ...prev, ...fetched }));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [cur]);

  async function act(body) {
    if (!cur || !workspaceId) return;
    setBusy(true);
    try {
      await decideWorkspaceSmartDedupConflict(workspaceId, cur.id, body);
      await onMerged?.();
      await reload();
    } catch {
      /* ignore */
    } finally {
      setBusy(false);
    }
  }

  if (!workspaceId) return null;
  if (loadErr) {
    return (
      <Box sx={{ mt: 2, p: 1.5, borderRadius: "6px", border: "1px solid rgba(239,68,68,0.35)", backgroundColor: "rgba(239,68,68,0.06)" }}>
        <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)" }}>{loadErr}</Typography>
        <CursorSmallButton sx={{ mt: 1 }} type="button" onClick={() => void reload()}>
          {t("workspace.err.retry")}
        </CursorSmallButton>
        <CursorSmallButton sx={{ mt: 1, ml: 1 }} type="button" onClick={() => onDismiss?.()}>
          {t("workspace.ingestDedup.dismiss")}
        </CursorSmallButton>
      </Box>
    );
  }
  if (!items.length) return null;

  const score = cur?.similarity_score != null ? Number(cur.similarity_score).toFixed(3) : "—";

  return (
    <Box
      sx={{
        mt: 2,
        p: 1.5,
        borderRadius: "6px",
        border: "1px solid rgba(129,140,248,0.35)",
        backgroundColor: "rgba(99,102,241,0.08)",
      }}
    >
      <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: "rgba(255,255,255,0.92)", mb: 0.5 }}>
        {t("workspace.ingestDedup.title")}
      </Typography>
      <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.5)", mb: 1.25 }}>
        {t("workspace.ingestDedup.subtitle", {
          current: String(safeIdx + 1),
          total: String(items.length),
          score,
        })}
      </Typography>
      {items.length > 1 ? (
        <Box sx={{ display: "flex", gap: 0.5, mb: 1, alignItems: "center", flexWrap: "wrap" }}>
          <CursorSmallButton
            type="button"
            disabled={busy || safeIdx <= 0}
            onClick={() => setIdx((i) => Math.max(0, i - 1))}
            aria-label={t("workspace.ingestDedup.prev")}
          >
            <ChevronLeftIcon sx={{ fontSize: "1.05rem", mr: 0.25, verticalAlign: "middle" }} />
            {t("workspace.ingestDedup.prev")}
          </CursorSmallButton>
          <CursorSmallButton
            type="button"
            disabled={busy || safeIdx >= items.length - 1}
            onClick={() => setIdx((i) => Math.min(items.length - 1, i + 1))}
            aria-label={t("workspace.ingestDedup.next")}
          >
            {t("workspace.ingestDedup.next")}
            <ChevronRightIcon sx={{ fontSize: "1.05rem", ml: 0.25, verticalAlign: "middle" }} />
          </CursorSmallButton>
        </Box>
      ) : null}
      {cur?.id ? (
        <Typography
          sx={{
            fontSize: "0.65rem",
            color: "rgba(255,255,255,0.38)",
            mb: activeIngestJobId ? 0.5 : 1,
            fontFamily: "ui-monospace, monospace",
          }}
        >
          {t("workspace.ingestDedup.conflictId", { id: String(cur.id) })}
        </Typography>
      ) : null}
      {activeIngestJobId ? (
        <Typography sx={{ fontSize: "0.65rem", color: "rgba(255,255,255,0.38)", mb: 1 }}>
          {t("workspace.ingestDedup.jobContext", { id: activeIngestJobId })}
        </Typography>
      ) : null}
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 1.25 }}>
        <Box sx={{ p: 1, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.1)", backgroundColor: "#141414" }}>
          <Typography sx={{ fontSize: "0.65rem", color: "rgba(129,140,248,0.95)", mb: 0.5 }}>{t("workspace.ingestDedup.workA")}</Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.88)" }}>
            {titles[cur.work_id_a] || t("workspace.ingestDedup.loadingTitles")}
          </Typography>
        </Box>
        <Box sx={{ p: 1, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.1)", backgroundColor: "#141414" }}>
          <Typography sx={{ fontSize: "0.65rem", color: "rgba(129,140,248,0.95)", mb: 0.5 }}>{t("workspace.ingestDedup.workB")}</Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.88)" }}>
            {titles[cur.work_id_b] || t("workspace.ingestDedup.loadingTitles")}
          </Typography>
        </Box>
      </Box>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, mt: 1.25 }}>
        <CursorSmallButton
          type="button"
          disabled={busy}
          onClick={() => act({ decision: "merge", keep_work_id: cur.work_id_a })}
        >
          {t("workspace.ingestDedup.mergeKeepA")}
        </CursorSmallButton>
        <CursorSmallButton
          type="button"
          disabled={busy}
          onClick={() => act({ decision: "merge", keep_work_id: cur.work_id_b })}
        >
          {t("workspace.ingestDedup.mergeKeepB")}
        </CursorSmallButton>
        <CursorSmallButton type="button" disabled={busy} onClick={() => act({ decision: "keep_separate" })}>
          {t("workspace.ingestDedup.keepSeparate")}
        </CursorSmallButton>
        <CursorSmallButton type="button" disabled={busy} onClick={() => act({ decision: "skip" })}>
          {t("workspace.ingestDedup.skip")}
        </CursorSmallButton>
        <CursorSmallButton type="button" disabled={busy} onClick={() => onDismiss?.()}>
          {t("workspace.ingestDedup.dismiss")}
        </CursorSmallButton>
      </Box>
    </Box>
  );
}
