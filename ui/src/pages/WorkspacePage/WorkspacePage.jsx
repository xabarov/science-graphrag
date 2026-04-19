import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Alert from "@mui/material/Alert";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import LinearProgress from "@mui/material/LinearProgress";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { CursorPrimaryButton, CursorSmallButton } from "../../components/common/index.js";
import DeduplicationPanel from "../../components/graph/DeduplicationPanel.jsx";
import PageHeader from "../../components/layout/PageHeader.jsx";
import WorkIdGlossaryHint from "../../components/layout/WorkIdGlossaryHint.jsx";
import { mainShellContentSx } from "../../components/layout/mainShellContentSx.js";
import { formatResearchApiError, getWorkDetail } from "../../services/researchApi.js";
import {
  getActiveWorkspaceId,
  setActiveWorkspaceId,
  listWorkspaces,
  getWorkspace,
  addWorkToWorkspace,
  getIngestJob,
  startWorkspaceDocumentIngest,
} from "../../utils/workspaceStore.js";
import { persistWorkId } from "./utils/workContext.js";
import { rememberRecentWork } from "../HomePage/homeState.js";

function workReaderUrl(workId) {
  return `/reader?work_id=${encodeURIComponent(workId)}`;
}

function workGraphUrl(workId, workspaceId) {
  const p = new URLSearchParams();
  if (workspaceId) p.set("workspace_id", workspaceId);
  if (workId && String(workId).trim()) p.set("work_id", String(workId).trim());
  const qs = p.toString();
  return qs ? `/graph?${qs}` : "/graph";
}

function workAskUrl(workId) {
  return `/ask?work_id=${encodeURIComponent(workId)}`;
}

function workEvidenceUrl(workId) {
  return `/evidence?work_id=${encodeURIComponent(workId)}`;
}

/**
 * @param {{ workId: string, title: string, year?: number | null, doi?: string | null, arxivId?: string | null, loading?: boolean, error?: string | null, workspaceId?: string }} props
 */
function WorkPaperCard({ workId, title, year, doi, arxivId, loading, error, workspaceId }) {
  return (
    <Box
      sx={{
        p: 1.75,
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "#1a1a1a",
        maxWidth: 720,
      }}
    >
      {loading ? (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 1 }}>
          <CircularProgress size={20} sx={{ color: "rgba(129,140,248,0.9)" }} />
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)" }}>Loading paper…</Typography>
        </Box>
      ) : null}
      {error ? (
        <Alert severity="error" sx={{ mb: 1.5, fontSize: "0.8125rem" }}>
          {error}
        </Alert>
      ) : null}
      {!loading && !error ? (
        <>
          <Typography sx={{ fontWeight: 600, fontSize: "0.9375rem", color: "rgba(255,255,255,0.9)" }}>
            {title || "(no title)"}
          </Typography>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.5, fontFamily: "monospace" }}>
            {workId}
          </Typography>
          <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 0.75 }}>
            {year != null ? <Chip label={`Year ${year}`} size="small" sx={{ height: 22, fontSize: "0.6875rem" }} /> : null}
            {doi ? <Chip label={`DOI ${String(doi).slice(0, 24)}…`} size="small" sx={{ height: 22, fontSize: "0.6875rem" }} /> : null}
            {arxivId ? <Chip label={`arXiv ${arxivId}`} size="small" sx={{ height: 22, fontSize: "0.6875rem" }} /> : null}
          </Box>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.42)", mt: 1.25 }}>
            Open the reader for extracted text; use the left rail for Graph, Ask, and Evidence with the same{" "}
            <code style={{ fontSize: "0.7rem" }}>work_id</code>.
          </Typography>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mt: 1.25 }}>
            <CursorPrimaryButton component={Link} to={workReaderUrl(workId)} sx={{ textDecoration: "none", fontSize: "0.8125rem" }}>
              Reader
            </CursorPrimaryButton>
            <CursorSmallButton component={Link} to={workGraphUrl(workId, workspaceId)} sx={{ textDecoration: "none" }}>
              Graph
            </CursorSmallButton>
            <CursorSmallButton component={Link} to={workAskUrl(workId)} sx={{ textDecoration: "none" }}>
              Ask
            </CursorSmallButton>
            <CursorSmallButton component={Link} to={workEvidenceUrl(workId)} sx={{ textDecoration: "none" }}>
              Evidence
            </CursorSmallButton>
          </Box>
        </>
      ) : null}
    </Box>
  );
}

export default function WorkspacePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const workspaceIdFromUrl = (searchParams.get("workspace_id") || "").trim();
  const workIdFromUrl = (searchParams.get("work_id") || "").trim();

  const [workspaceMeta, setWorkspaceMeta] = useState({ id: "", name: "", work_ids: [] });
  const [workspaceLoading, setWorkspaceLoading] = useState(true);
  const [workspaceError, setWorkspaceError] = useState(null);
  const [addWorkInput, setAddWorkInput] = useState("");
  const [addBusy, setAddBusy] = useState(false);
  const [addErr, setAddErr] = useState(null);

  const [papers, setPapers] = useState(() => new Map());
  const [ingestJobId, setIngestJobId] = useState("");
  const [ingestJob, setIngestJob] = useState(null);
  const [ingestErr, setIngestErr] = useState(null);
  const [uploadBusy, setUploadBusy] = useState(false);

  const refreshWorkspaceMeta = useCallback(async () => {
    const id = workspaceMeta.id;
    if (!id) return;
    try {
      const ws = await getWorkspace(id);
      if (ws) setWorkspaceMeta(ws);
    } catch {
      /* ignore */
    }
  }, [workspaceMeta.id]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setWorkspaceLoading(true);
      setWorkspaceError(null);
      try {
        const list = await listWorkspaces();
        if (cancelled) return;
        let activeId = workspaceIdFromUrl || getActiveWorkspaceId();
        if (!activeId && list.length) activeId = list[0].id;
        if (!activeId) {
          setWorkspaceMeta({ id: "", name: "", work_ids: [] });
          return;
        }
        setActiveWorkspaceId(activeId);
        const ws = await getWorkspace(activeId);
        if (cancelled) return;
        if (!ws) {
          setWorkspaceError("Workspace not found.");
          setWorkspaceMeta({ id: "", name: "", work_ids: [] });
          return;
        }
        setWorkspaceMeta(ws);
        const nextParams = new URLSearchParams();
        nextParams.set("workspace_id", ws.id);
        const ids = Array.isArray(ws.work_ids) ? ws.work_ids : [];
        if (ids.length === 1) {
          nextParams.set("work_id", ids[0]);
        } else if (workIdFromUrl && ids.includes(workIdFromUrl)) {
          nextParams.set("work_id", workIdFromUrl);
        }
        setSearchParams(nextParams, { replace: true });
      } catch (e) {
        if (!cancelled) setWorkspaceError(formatResearchApiError(e));
      } finally {
        if (!cancelled) setWorkspaceLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workspaceIdFromUrl, workIdFromUrl, setSearchParams]);

  const effectiveWorkIds = useMemo(() => {
    const fromWs = Array.isArray(workspaceMeta.work_ids) ? workspaceMeta.work_ids : [];
    if (fromWs.length) return fromWs;
    return [];
  }, [workspaceMeta.work_ids]);

  const workIdsKey = effectiveWorkIds.join("|");

  useEffect(() => {
    if (!effectiveWorkIds.length) return;
    let cancelled = false;
    (async () => {
      for (const wid of effectiveWorkIds) {
        setPapers((prev) => {
          const m = new Map(prev);
          const cur = m.get(wid) || {};
          m.set(wid, { ...cur, workId: wid, loading: true, error: null });
          return m;
        });
        try {
          const res = await getWorkDetail(wid);
          if (cancelled) return;
          const d = res.data;
          setPapers((prev) => {
            const m = new Map(prev);
            m.set(wid, {
              workId: wid,
              title: typeof d?.title === "string" ? d.title : "",
              year: d?.year ?? null,
              doi: d?.doi ?? null,
              arxivId: d?.arxiv_id ?? null,
              loading: false,
              error: null,
            });
            return m;
          });
          rememberRecentWork({
            workId: wid,
            title: typeof d?.title === "string" ? d.title : "",
            year: d?.year ?? null,
            tab: "overview",
          });
        } catch (err) {
          if (cancelled) return;
          setPapers((prev) => {
            const m = new Map(prev);
            m.set(wid, {
              workId: wid,
              title: "",
              loading: false,
              error: formatResearchApiError(err),
            });
            return m;
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workIdsKey, effectiveWorkIds]);

  useEffect(() => {
    const primary = effectiveWorkIds[0] || workIdFromUrl;
    if (primary) persistWorkId(primary);
  }, [effectiveWorkIds, workIdFromUrl]);

  useEffect(() => {
    if (!ingestJobId) return undefined;
    let cancelled = false;
    const tick = async () => {
      try {
        const j = await getIngestJob(ingestJobId);
        if (cancelled) return;
        setIngestJob(j);
        if (j?.status === "completed" || j?.status === "failed") {
          await refreshWorkspaceMeta();
          setIngestJobId("");
        }
      } catch {
        /* ignore transient poll errors */
      }
    };
    tick();
    const id = setInterval(tick, 2000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [ingestJobId, refreshWorkspaceMeta]);

  const emptyState = useMemo(
    () => (
      <Box sx={{ maxWidth: 560, mt: 2 }}>
        <Alert severity="info" sx={{ fontSize: "0.8125rem", mb: 2, backgroundColor: "rgba(99,102,241,0.08)", color: "rgba(255,255,255,0.85)" }}>
          No workspace yet. Create one under Workspaces, then upload a PDF / text or attach an existing indexed <code>work_id</code>.
        </Alert>
        <CursorPrimaryButton component={Link} to="/workspaces" sx={{ textDecoration: "none" }}>
          Workspaces
        </CursorPrimaryButton>
        <CursorSmallButton component={Link} to="/home" sx={{ textDecoration: "none", ml: 1 }}>
          About
        </CursorSmallButton>
      </Box>
    ),
    [],
  );

  async function handleAddWork(e) {
    e?.preventDefault?.();
    const raw = addWorkInput.trim();
    if (!raw || !workspaceMeta.id) return;
    setAddBusy(true);
    setAddErr(null);
    try {
      await addWorkToWorkspace(workspaceMeta.id, raw);
      setAddWorkInput("");
      const ws = await getWorkspace(workspaceMeta.id);
      if (ws) setWorkspaceMeta(ws);
    } catch (err) {
      setAddErr(formatResearchApiError(err));
    } finally {
      setAddBusy(false);
    }
  }

  async function handleUploadDocument(ev) {
    const file = ev.target.files?.[0];
    ev.target.value = "";
    if (!file || !workspaceMeta.id) return;
    setUploadBusy(true);
    setIngestErr(null);
    try {
      const job = await startWorkspaceDocumentIngest(workspaceMeta.id, file);
      const jid = String(job?.job_id || "").trim();
      if (jid) {
        setIngestJob(job);
        setIngestJobId(jid);
      }
    } catch (err) {
      setIngestErr(formatResearchApiError(err));
    } finally {
      setUploadBusy(false);
    }
  }

  return (
    <Box sx={{ p: { xs: 1.5, sm: 2 }, ...mainShellContentSx }}>
      <PageHeader
        eyebrow="Workspace"
        title={workspaceMeta.name || "Papers"}
        description={
          workspaceLoading ? (
            <Box sx={{ display: "inline-flex", alignItems: "center", gap: 1 }}>
              <CircularProgress size={18} sx={{ color: "rgba(129,140,248,0.9)" }} />
              <span>Loading workspace…</span>
            </Box>
          ) : workspaceMeta.id ? (
            <>
              <span style={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem" }}>
                {effectiveWorkIds.length} paper{effectiveWorkIds.length === 1 ? "" : "s"} in this workspace.
              </span>
              <br />
              <span style={{ color: "rgba(255,255,255,0.38)", fontFamily: "monospace", fontSize: "0.72rem" }}>
                {workspaceMeta.id}
              </span>
            </>
          ) : (
            <WorkIdGlossaryHint variant="workspace" />
          )
        }
        actions={
          workspaceMeta.id ? (
            <CursorSmallButton component={Link} to={workGraphUrl("", workspaceMeta.id)} sx={{ textDecoration: "none" }}>
              Workspace graph
            </CursorSmallButton>
          ) : null
        }
      />

      {workspaceError ? (
        <Alert severity="error" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {workspaceError}
        </Alert>
      ) : null}

      {!workspaceLoading && !workspaceMeta.id ? (
        emptyState
      ) : (
        <>
          {workspaceMeta.id ? (
            <Box
              sx={{
                mb: 2,
                p: 1.5,
                borderRadius: "6px",
                border: "1px solid rgba(99,102,241,0.22)",
                backgroundColor: "rgba(99,102,241,0.06)",
                maxWidth: 560,
              }}
            >
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)", mb: 1 }}>Upload article</Typography>
              <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.45)", mb: 1.25, lineHeight: 1.45 }}>
                PDF, Markdown, or plain text. Processing runs on the server; this page polls until done, then refreshes the paper list.
              </Typography>
              <input type="file" accept=".pdf,.md,.txt" hidden id="workspace-ingest-input" onChange={(e) => handleUploadDocument(e)} />
              <label htmlFor="workspace-ingest-input">
                <CursorPrimaryButton component="span" disabled={uploadBusy || Boolean(ingestJobId)} sx={{ cursor: "pointer" }}>
                  {uploadBusy ? "Starting…" : ingestJobId ? "Processing…" : "Choose file"}
                </CursorPrimaryButton>
              </label>
              {ingestErr ? (
                <Alert severity="warning" sx={{ mt: 1.25, fontSize: "0.75rem" }}>
                  {ingestErr}
                </Alert>
              ) : null}
              {ingestJob ? (
                <Box sx={{ mt: 1.5 }}>
                  <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.5)", fontFamily: "monospace" }}>
                    job {ingestJob.job_id} · {ingestJob.status}
                  </Typography>
                  <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)", mt: 0.5 }}>{ingestJob.message || "—"}</Typography>
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
                  {ingestJob.work_id ? (
                    <Typography sx={{ fontSize: "0.72rem", color: "rgba(129,140,248,0.9)", mt: 0.75 }}>
                      New work_id: <code>{ingestJob.work_id}</code>
                    </Typography>
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
          ) : null}

          {workspaceMeta.id ? (
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
              <AccordionSummary sx={{ fontSize: "0.8125rem", fontWeight: 600 }}>Advanced: add existing work_id</AccordionSummary>
              <AccordionDetails sx={{ pt: 0 }}>
                <Box component="form" onSubmit={handleAddWork} sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "flex-start" }}>
                  <TextField
                    label="work_id"
                    value={addWorkInput}
                    onChange={(ev) => setAddWorkInput(ev.target.value)}
                    size="small"
                    placeholder="Existing indexed work id"
                    sx={{
                      minWidth: 220,
                      flex: "1 1 200px",
                      "& .MuiInputBase-input": { fontSize: "0.8125rem" },
                      "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
                    }}
                  />
                  <CursorPrimaryButton type="submit" disabled={addBusy || !addWorkInput.trim()}>
                    Add to workspace
                  </CursorPrimaryButton>
                </Box>
              </AccordionDetails>
            </Accordion>
          ) : null}
          {addErr ? (
            <Alert severity="warning" sx={{ mb: 2, fontSize: "0.8125rem" }}>
              {addErr}
            </Alert>
          ) : null}

          <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
            {workspaceMeta.id && effectiveWorkIds.length === 0 ? (
              <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>
                No papers yet. Upload a file above, or add an existing <code>work_id</code> from the catalog under Workspaces.
              </Typography>
            ) : null}
            {effectiveWorkIds.map((wid) => {
              const row = papers.get(wid);
              return (
                <WorkPaperCard
                  key={wid}
                  workId={wid}
                  title={row?.title || ""}
                  year={row?.year}
                  doi={row?.doi}
                  arxivId={row?.arxivId}
                  loading={row?.loading}
                  error={row?.error}
                  workspaceId={workspaceMeta.id}
                />
              );
            })}
          </Box>

          {workspaceMeta.id ? (
            <Box sx={{ mt: 2.5 }}>
              <DeduplicationPanel workspaceId={workspaceMeta.id} onMerged={() => refreshWorkspaceMeta()} />
            </Box>
          ) : null}
        </>
      )}
    </Box>
  );
}
