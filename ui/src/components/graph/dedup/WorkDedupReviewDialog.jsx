import React, { useCallback, useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import Radio from "@mui/material/Radio";
import RadioGroup from "@mui/material/RadioGroup";
import Typography from "@mui/material/Typography";

import { formatResearchApiError, getWorkDetail } from "../../../services/researchApi.js";
import { decideWorkspaceSmartDedupConflict } from "../../../utils/workspaceStore.js";

/**
 * @param {{
 *   open: boolean,
 *   onClose: () => void,
 *   workspaceId: string,
 *   conflict: Record<string, unknown> | null,
 *   onDecided: () => void,
 * }} props
 */
export default function WorkDedupReviewDialog({ open, onClose, workspaceId, conflict, onDecided }) {
  const [choice, setChoice] = useState("merge_a");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [detailA, setDetailA] = useState(null);
  const [detailB, setDetailB] = useState(null);

  const wa = conflict?.work_id_a != null ? String(conflict.work_id_a) : "";
  const wb = conflict?.work_id_b != null ? String(conflict.work_id_b) : "";

  useEffect(() => {
    if (!open || !wa || !wb) return;
    let cancelled = false;
    (async () => {
      setErr(null);
      try {
        const [ra, rb] = await Promise.all([getWorkDetail(wa), getWorkDetail(wb)]);
        if (!cancelled) {
          setDetailA(ra?.data ?? null);
          setDetailB(rb?.data ?? null);
        }
      } catch (e) {
        if (!cancelled) setErr(formatResearchApiError(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, wa, wb]);

  const sim = useMemo(() => {
    const s = conflict?.similarity_score;
    const n = Number(s);
    return Number.isFinite(n) ? n.toFixed(3) : "—";
  }, [conflict]);

  const submit = useCallback(async () => {
    if (!workspaceId || !conflict?.id) return;
    setBusy(true);
    setErr(null);
    try {
      await decideWorkspaceSmartDedupConflict(workspaceId, String(conflict.id), choice);
      onDecided();
      onClose();
    } catch (e) {
      setErr(formatResearchApiError(e));
    } finally {
      setBusy(false);
    }
  }, [choice, conflict, onClose, onDecided, workspaceId]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Review duplicate pair</DialogTitle>
      <DialogContent>
        {err ? (
          <Typography color="error" sx={{ mb: 2, fontSize: "0.8125rem" }}>
            {err}
          </Typography>
        ) : null}
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)", mb: 1 }}>
          Cosine similarity (work summary vectors): <strong>{sim}</strong>
          {conflict?.check_mode ? ` · mode: ${String(conflict.check_mode)}` : ""}
        </Typography>
        {conflict?.llm_reason ? (
          <Typography sx={{ fontSize: "0.8125rem", mb: 2, whiteSpace: "pre-wrap" }}>
            LLM note: {String(conflict.llm_reason)}
          </Typography>
        ) : null}
        <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2, mt: 1 }}>
          <PaperSide label="Work A" workId={wa} detail={detailA} />
          <PaperSide label="Work B" workId={wb} detail={detailB} />
        </Box>
        <FormControl sx={{ mt: 2 }}>
          <RadioGroup value={choice} onChange={(e) => setChoice(e.target.value)}>
            <FormControlLabel value="merge_a" control={<Radio size="small" />} label="Keep A (merge into A)" />
            <FormControlLabel value="merge_b" control={<Radio size="small" />} label="Keep B (merge into B)" />
            <FormControlLabel value="keep_separate" control={<Radio size="small" />} label="Keep separate" />
            <FormControlLabel value="skip" control={<Radio size="small" />} label="Skip for now" />
          </RadioGroup>
        </FormControl>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={busy}>
          Cancel
        </Button>
        <Button variant="contained" onClick={() => void submit()} disabled={busy}>
          {busy ? "Saving…" : "Submit"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

/** @param {{ label: string, workId: string, detail: Record<string, unknown> | null }} props */
function PaperSide({ label, workId, detail }) {
  const title = detail?.title != null ? String(detail.title) : "…";
  const year =
    detail?.year != null
      ? String(detail.year)
      : detail?.publication_year != null
        ? String(detail.publication_year)
        : "";
  const doi = detail?.doi != null ? String(detail.doi) : "";
  const ab = detail?.abstract != null ? String(detail.abstract).slice(0, 600) : "";
  return (
    <Box sx={{ p: 1.5, borderRadius: 1, border: "1px solid rgba(255,255,255,0.1)", bgcolor: "#141414" }}>
      <Typography sx={{ fontSize: "0.7rem", color: "rgba(129,140,248,0.9)" }}>{label}</Typography>
      <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", mt: 0.5 }}>{title}</Typography>
      <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.45)", mt: 0.5 }}>
        <code>{workId}</code>
        {year ? ` · ${year}` : ""}
        {doi ? ` · DOI ${doi}` : ""}
      </Typography>
      {ab ? (
        <Typography sx={{ fontSize: "0.75rem", mt: 1, color: "rgba(255,255,255,0.7)", whiteSpace: "pre-wrap" }}>
          {ab}
          {String(detail?.abstract || "").length > 600 ? "…" : ""}
        </Typography>
      ) : null}
    </Box>
  );
}
