import React, { useCallback, useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Alert from "@mui/material/Alert";
import Typography from "@mui/material/Typography";

import { CursorPrimaryButton, CursorSmallButton } from "../common/index.js";
import { formatResearchApiError, getWorkDetail } from "../../services/researchApi.js";
import { getWorkspaceDedupCandidates, mergeWorksInWorkspace } from "../../utils/workspaceStore.js";

/**
 * @param {{ workspaceId: string, onMerged?: () => void }} props
 */
export default function DeduplicationPanel({ workspaceId, onMerged }) {
  const [items, setItems] = useState([]);
  const [index, setIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [titles, setTitles] = useState(() => ({}));

  const load = useCallback(async () => {
    const wid = String(workspaceId || "").trim();
    if (!wid) {
      setItems([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const rows = await getWorkspaceDedupCandidates(wid);
      setItems(rows);
      setIndex(0);
    } catch (e) {
      setError(formatResearchApiError(e));
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    load();
  }, [load]);

  const current = items[index] || null;
  const wids = current && Array.isArray(current.work_ids) ? current.work_ids : [];

  useEffect(() => {
    const row = items[index];
    const ids = Array.isArray(row?.work_ids) ? row.work_ids : [];
    if (!ids.length) {
      setTitles({});
      return;
    }
    let cancelled = false;
    (async () => {
      const next = {};
      for (const id of ids.slice(0, 5)) {
        try {
          const res = await getWorkDetail(id);
          if (cancelled) return;
          const t = typeof res.data?.title === "string" ? res.data.title : "";
          next[id] = t || id;
        } catch {
          next[id] = id;
        }
      }
      if (!cancelled) setTitles(next);
    })();
    return () => {
      cancelled = true;
    };
  }, [items, index]);

  async function decide(keepIdx, dropIdx) {
    const wid = String(workspaceId || "").trim();
    if (!wid || keepIdx < 0 || dropIdx < 0 || keepIdx >= wids.length || dropIdx >= wids.length) return;
    const keep = String(wids[keepIdx] || "").trim();
    const drop = String(wids[dropIdx] || "").trim();
    if (!keep || !drop || keep === drop) return;
    setBusy(true);
    setError(null);
    try {
      await mergeWorksInWorkspace(wid, keep, drop);
      await load();
      onMerged?.();
    } catch (e) {
      setError(formatResearchApiError(e));
    } finally {
      setBusy(false);
    }
  }

  async function skipCluster() {
    setIndex((i) => Math.min(items.length - 1, i + 1));
  }

  if (!String(workspaceId || "").trim()) {
    return null;
  }

  return (
    <Box
      sx={{
        mt: 1,
        p: 1.5,
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "#141414",
        maxWidth: 640,
      }}
    >
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.9)", mb: 0.75 }}>
        Review duplicate papers (workspace scope)
      </Typography>
      <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.45)", mb: 1, lineHeight: 1.45 }}>
        Clusters share the same DOI, arXiv id, OpenAlex id, or fingerprint. Choose which work to keep; merge re-points citations onto the kept work
        and syncs Qdrant payloads when the duplicate node is removed from Neo4j.
      </Typography>
      {loading ? (
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>Loading candidates…</Typography>
      ) : null}
      {error ? (
        <Alert severity="error" sx={{ mb: 1, fontSize: "0.75rem" }}>
          {error}
        </Alert>
      ) : null}
      {!loading && items.length === 0 ? (
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}>No duplicate clusters in this workspace.</Typography>
      ) : null}
      {current ? (
        <Box>
          <Typography sx={{ fontSize: "0.7rem", color: "rgba(129,140,248,0.9)", mb: 0.75 }}>
            Candidate {index + 1} / {items.length} · {String(current.kind || "")} · key{" "}
            {String(current.dedup_key || "").slice(0, 48)}
            {String(current.dedup_key || "").length > 48 ? "…" : ""}
          </Typography>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
            {wids.map((id, i) => (
              <Box
                key={`${id}-${i}`}
                sx={{
                  p: 1,
                  borderRadius: "6px",
                  border: "1px solid rgba(255,255,255,0.08)",
                  backgroundColor: "#1a1a1a",
                }}
              >
                <Typography sx={{ fontWeight: 600, fontSize: "0.78rem", color: "rgba(255,255,255,0.88)" }} noWrap title={titles[id] || id}>
                  {titles[id] || "Loading title…"}
                </Typography>
                <Typography sx={{ fontFamily: "monospace", fontSize: "0.68rem", color: "rgba(255,255,255,0.42)", mt: 0.35 }} noWrap>
                  {id}
                </Typography>
              </Box>
            ))}
          </Box>
          {wids.length >= 2 ? (
            <Box sx={{ mt: 1.25, display: "flex", flexDirection: "column", gap: 0.75 }}>
              <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.45)" }}>Merge actions</Typography>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
                <CursorPrimaryButton type="button" disabled={busy} onClick={() => decide(0, 1)} sx={{ fontSize: "0.75rem" }}>
                  Keep 1, merge 2
                </CursorPrimaryButton>
                <CursorPrimaryButton type="button" disabled={busy} onClick={() => decide(1, 0)} sx={{ fontSize: "0.75rem" }}>
                  Keep 2, merge 1
                </CursorPrimaryButton>
                {wids.length > 2 ? (
                  <CursorSmallButton type="button" disabled={busy} onClick={() => decide(0, 2)} sx={{ fontSize: "0.75rem" }}>
                    Keep 1 · merge 3
                  </CursorSmallButton>
                ) : null}
              </Box>
            </Box>
          ) : null}
          <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 0.75 }}>
            <CursorSmallButton type="button" disabled={busy} onClick={() => skipCluster()}>
              Skip for now
            </CursorSmallButton>
            <CursorSmallButton type="button" disabled={busy || index >= items.length - 1} onClick={() => setIndex((i) => Math.min(items.length - 1, i + 1))}>
              Next
            </CursorSmallButton>
            <CursorSmallButton type="button" disabled={busy || index <= 0} onClick={() => setIndex((i) => Math.max(0, i - 1))}>
              Prev
            </CursorSmallButton>
            <CursorSmallButton type="button" disabled={busy || loading} onClick={() => load()}>
              Refresh list
            </CursorSmallButton>
          </Box>
        </Box>
      ) : null}
    </Box>
  );
}
