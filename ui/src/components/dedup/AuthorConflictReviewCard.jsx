import React, { useCallback, useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { decideWorkspaceAuthorDedupConflict, getWorkspaceAuthorDedupConflicts } from "../../utils/workspaceStore.js";

/**
 * Review queue for author pairs created during ingest (origin=ingest).
 *
 * @param {{
 *   workspaceId: string,
 *   onDismiss: () => void,
 *   onMerged: () => void | Promise<void>,
 * }} props
 */
export default function AuthorConflictReviewCard({ workspaceId, onDismiss, onMerged }) {
  const { t } = useI18n();
  const [items, setItems] = useState([]);
  const [idx, setIdx] = useState(0);
  const [busy, setBusy] = useState(false);
  const [loadErr, setLoadErr] = useState("");

  const reload = useCallback(async () => {
    if (!workspaceId) return;
    setLoadErr("");
    try {
      const data = await getWorkspaceAuthorDedupConflicts(workspaceId, {
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

  const safeIdx = items.length ? Math.min(idx, items.length - 1) : 0;
  const cur = items.length ? items[safeIdx] : null;

  async function act(body) {
    if (!cur || !workspaceId) return;
    setBusy(true);
    try {
      await decideWorkspaceAuthorDedupConflict(workspaceId, cur.id, body);
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
          {t("workspace.ingestAuthorDedup.dismiss")}
        </CursorSmallButton>
      </Box>
    );
  }
  if (!items.length) return null;

  const score = cur?.similarity_score != null ? Number(cur.similarity_score).toFixed(3) : "—";
  const nameA = String(cur?.author_name_a || cur?.author_id_a || "").trim() || t("workspace.ingestAuthorDedup.loadingNames");
  const nameB = String(cur?.author_name_b || cur?.author_id_b || "").trim() || t("workspace.ingestAuthorDedup.loadingNames");

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
        {t("workspace.ingestAuthorDedup.title")}
      </Typography>
      <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.5)", mb: 1.25 }}>
        {t("workspace.ingestAuthorDedup.subtitle", {
          current: String(idx + 1),
          total: String(items.length),
          score,
        })}
      </Typography>
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 1.25 }}>
        <Box sx={{ p: 1, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.1)", backgroundColor: "#141414" }}>
          <Typography sx={{ fontSize: "0.65rem", color: "rgba(129,140,248,0.95)", mb: 0.5 }}>{t("workspace.ingestAuthorDedup.authorA")}</Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.88)" }}>{nameA}</Typography>
        </Box>
        <Box sx={{ p: 1, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.1)", backgroundColor: "#141414" }}>
          <Typography sx={{ fontSize: "0.65rem", color: "rgba(129,140,248,0.95)", mb: 0.5 }}>{t("workspace.ingestAuthorDedup.authorB")}</Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.88)" }}>{nameB}</Typography>
        </Box>
      </Box>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, mt: 1.25 }}>
        <CursorSmallButton type="button" disabled={busy} onClick={() => act({ decision: "merge_a" })}>
          {t("workspace.ingestAuthorDedup.mergeKeepA")}
        </CursorSmallButton>
        <CursorSmallButton type="button" disabled={busy} onClick={() => act({ decision: "merge_b" })}>
          {t("workspace.ingestAuthorDedup.mergeKeepB")}
        </CursorSmallButton>
        <CursorSmallButton type="button" disabled={busy} onClick={() => act({ decision: "keep_separate" })}>
          {t("workspace.ingestAuthorDedup.keepSeparate")}
        </CursorSmallButton>
        <CursorSmallButton type="button" disabled={busy} onClick={() => act({ decision: "skip" })}>
          {t("workspace.ingestAuthorDedup.skip")}
        </CursorSmallButton>
        <CursorSmallButton type="button" disabled={busy} onClick={() => onDismiss?.()}>
          {t("workspace.ingestAuthorDedup.dismiss")}
        </CursorSmallButton>
      </Box>
    </Box>
  );
}
