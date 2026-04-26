import React, { useCallback, useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../common/index.js";
import { useI18n } from "../../i18n/I18nContext.jsx";
import { decideEntityDedupConflict, listEntityDedupConflicts } from "../../utils/workspaceStore.js";

const ENTITY_TYPES = ["institution", "venue", "method", "dataset"];

/**
 * Review queue for entity pairs created during ingest (origin=ingest), all Wave T types.
 *
 * @param {{
 *   workspaceId: string,
 *   onDismiss: () => void,
 *   onMerged: () => void | Promise<void>,
 * }} props
 */
export default function EntityConflictReviewCard({ workspaceId, onDismiss, onMerged }) {
  const { t } = useI18n();
  const [items, setItems] = useState([]);
  const [idx, setIdx] = useState(0);
  const [busy, setBusy] = useState(false);
  const [loadErr, setLoadErr] = useState("");

  const reload = useCallback(async () => {
    if (!workspaceId) return;
    setLoadErr("");
    try {
      const chunks = await Promise.all(
        ENTITY_TYPES.map((entityType) =>
          listEntityDedupConflicts({
            entityType,
            workspaceId,
            origin: "ingest",
            status: "pending",
            limit: 50,
          }),
        ),
      );
      const flat = [];
      chunks.forEach((data, i) => {
        const et = ENTITY_TYPES[i];
        const rows = Array.isArray(data?.items) ? data.items : [];
        rows.forEach((row) => flat.push({ ...row, entity_type: row.entity_type || et }));
      });
      setItems(flat);
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

  const isAliasType = cur && (cur.entity_type === "method" || cur.entity_type === "dataset");

  async function act(body) {
    if (!cur || !workspaceId) return;
    setBusy(true);
    try {
      await decideEntityDedupConflict(cur.id, { workspaceId, ...body });
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
          {t("workspace.ingestEntityDedup.dismiss")}
        </CursorSmallButton>
      </Box>
    );
  }
  if (!items.length) return null;

  const score = cur?.similarity_score != null ? Number(cur.similarity_score).toFixed(3) : "—";
  const et = String(cur?.entity_type || "entity");
  const labelA = String(cur?.entity_label_a || cur?.entity_id_a || "").trim() || t("workspace.ingestEntityDedup.loadingLabels");
  const labelB = String(cur?.entity_label_b || cur?.entity_id_b || "").trim() || t("workspace.ingestEntityDedup.loadingLabels");

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
        {t("workspace.ingestEntityDedup.title")}
      </Typography>
      <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.5)", mb: 1.25 }}>
        {t("workspace.ingestEntityDedup.subtitle", {
          current: String(idx + 1),
          total: String(items.length),
          entityType: et,
          score,
        })}
      </Typography>
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 1.25 }}>
        <Box sx={{ p: 1, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.1)", backgroundColor: "#141414" }}>
          <Typography sx={{ fontSize: "0.65rem", color: "rgba(129,140,248,0.95)", mb: 0.5 }}>{t("workspace.ingestEntityDedup.entityA")}</Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.88)" }}>{labelA}</Typography>
        </Box>
        <Box sx={{ p: 1, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.1)", backgroundColor: "#141414" }}>
          <Typography sx={{ fontSize: "0.65rem", color: "rgba(129,140,248,0.95)", mb: 0.5 }}>{t("workspace.ingestEntityDedup.entityB")}</Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.88)" }}>{labelB}</Typography>
        </Box>
      </Box>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, mt: 1.25 }}>
        {isAliasType ? (
          <>
            <CursorSmallButton
              type="button"
              disabled={busy}
              onClick={() => act({ decision: "merge", keep_entity_id: cur.entity_id_a })}
            >
              {t("workspace.ingestEntityDedup.aliasKeepA")}
            </CursorSmallButton>
            <CursorSmallButton
              type="button"
              disabled={busy}
              onClick={() => act({ decision: "merge", keep_entity_id: cur.entity_id_b })}
            >
              {t("workspace.ingestEntityDedup.aliasKeepB")}
            </CursorSmallButton>
          </>
        ) : (
          <>
            <CursorSmallButton
              type="button"
              disabled={busy}
              onClick={() => act({ decision: "merge", keep_entity_id: cur.entity_id_a })}
            >
              {t("workspace.ingestEntityDedup.mergeKeepA")}
            </CursorSmallButton>
            <CursorSmallButton
              type="button"
              disabled={busy}
              onClick={() => act({ decision: "merge", keep_entity_id: cur.entity_id_b })}
            >
              {t("workspace.ingestEntityDedup.mergeKeepB")}
            </CursorSmallButton>
          </>
        )}
        <CursorSmallButton type="button" disabled={busy} onClick={() => act({ decision: "skip" })}>
          {t("workspace.ingestEntityDedup.skip")}
        </CursorSmallButton>
        <CursorSmallButton type="button" disabled={busy} onClick={() => onDismiss?.()}>
          {t("workspace.ingestEntityDedup.dismiss")}
        </CursorSmallButton>
      </Box>
    </Box>
  );
}
