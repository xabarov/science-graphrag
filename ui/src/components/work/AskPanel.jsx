import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Alert from "@mui/material/Alert";
import Chip from "@mui/material/Chip";
import Autocomplete from "@mui/material/Autocomplete";
import Collapse from "@mui/material/Collapse";

import { CursorPrimaryButton, CursorSmallButton } from "../common/index.js";
import {
  buildAskAnswerRationale,
  buildQueryBody,
  formatRetrievalSummaryLines,
  getWorks,
  normalizeQueryResponse,
  postQuery,
} from "../../services/researchApi.js";
import { getAskHistory, rememberAskHistory } from "./askHistoryState.js";
import { buildStandaloneTracePath, buildWorkspaceTracePath } from "./traceabilityState.js";
import { persistWorkId } from "../../pages/WorkspacePage/utils/workContext.js";

function FlagChips({ label, items }) {
  if (!items || items.length === 0) return null;
  return (
    <Box sx={{ mt: 1 }}>
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 0.5 }}>{label}</Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
        {items.map((d) => (
          <Chip key={d} label={d} size="small" sx={{ height: 22, fontSize: "0.75rem" }} />
        ))}
      </Box>
    </Box>
  );
}

/**
 * @param {{
 *   scopedWorkId?: string | null,
 *   initialWorkId?: string,
 *   showPageChrome?: boolean,
 *   workspaceWorkId?: string | null,
 * }} props
 */
export default function AskPanel({
  scopedWorkId = null,
  initialWorkId = "",
  showPageChrome = true,
  workspaceWorkId = null,
}) {
  const locked = Boolean(scopedWorkId && String(scopedWorkId).trim());
  const [query, setQuery] = useState("object detection benchmarks");
  const [workId, setWorkId] = useState(locked ? String(scopedWorkId).trim() : initialWorkId);
  const [workOptions, setWorkOptions] = useState([]);
  const [topK, setTopK] = useState("5");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [normalized, setNormalized] = useState(null);
  const [history, setHistory] = useState([]);
  const [retrievalJsonOpen, setRetrievalJsonOpen] = useState(false);

  useEffect(() => {
    if (locked) {
      setWorkId(String(scopedWorkId).trim());
    } else {
      setWorkId(initialWorkId || "");
    }
  }, [locked, scopedWorkId, initialWorkId]);

  useEffect(() => {
    const recent = getAskHistory();
    setHistory(recent);
    if (!locked && !initialWorkId && recent[0]) {
      setQuery(recent[0].query);
      setWorkId(recent[0].workId);
      setTopK(String(recent[0].topK || 5));
    }
  }, [initialWorkId, locked]);

  useEffect(() => {
    let cancelled = false;
    getWorks({ limit: 80, offset: 0 })
      .then((res) => {
        if (!cancelled) setWorkOptions(res.data?.items || []);
      })
      .catch(() => {
        if (!cancelled) setWorkOptions([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const bodyPreview = useMemo(() => buildQueryBody(query, workId, topK), [query, workId, topK]);

  async function onSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setNormalized(null);
    setRetrievalJsonOpen(false);
    try {
      const res = await postQuery(bodyPreview);
      const nextNormalized = normalizeQueryResponse(res.data);
      setNormalized(nextNormalized);
      rememberAskHistory({
        query,
        workId,
        topK,
        answer: nextNormalized.answer,
        citationCount: nextNormalized.citations.length,
        mode: locked || inWorkspace ? "workspace" : workId ? "scoped" : "global",
      });
      setHistory(getAskHistory());
    } catch (err) {
      const msg = err?.response?.data?.detail
        ? JSON.stringify(err.response.data.detail)
        : err?.message || String(err);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  const inWorkspace = Boolean(workspaceWorkId && String(workspaceWorkId).trim());
  const standaloneMode = !inWorkspace && !locked;

  useEffect(() => {
    if (!locked && workId.trim()) {
      persistWorkId(workId);
    }
  }, [locked, workId]);

  return (
    <Box sx={{ maxWidth: 960 }}>
      {showPageChrome ? (
        <>
          <Typography sx={{ fontWeight: 600, mb: 1, color: "rgba(255,255,255,0.9)" }}>Ask</Typography>
          <Typography sx={{ color: "rgba(255,255,255,0.6)", fontSize: "0.8125rem", mb: 2 }}>
            POST /v1/query (live). Set <code style={{ color: "rgba(129,140,248,0.95)" }}>VITE_API_BASE_URL</code> if the API is not
            same-origin.
          </Typography>
        </>
      ) : (
        <Box
          sx={{
            mb: 2,
            p: 1.25,
            borderRadius: "6px",
            border: "1px solid rgba(99,102,241,0.2)",
            backgroundColor: "rgba(99,102,241,0.08)",
          }}
        >
          <Typography sx={{ color: "rgba(129,140,248,0.95)", fontSize: "0.75rem", mb: 0.5 }}>
            {inWorkspace || locked ? "Workspace-scoped research" : "Standalone research"}
          </Typography>
          <Typography sx={{ color: "rgba(255,255,255,0.78)", fontSize: "0.8125rem" }}>
            {inWorkspace || locked
              ? "Question is scoped to the active work. Use citations below to jump into evidence, reader context, and graph context without losing `work_id`."
              : "Ask across the corpus or pick one paper first. Use the answer actions below to move into evidence, reader context, or graph context when you need deeper inspection."}
          </Typography>
        </Box>
      )}

      {!locked && !workId.trim() ? (
        <Box
          sx={{
            mb: 2,
            p: 1.5,
            borderRadius: "6px",
            border: "1px dashed rgba(255,255,255,0.12)",
            backgroundColor: "rgba(255,255,255,0.02)",
          }}
        >
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)" }}>Optional work context</Typography>
          <Typography sx={{ mt: 0.6, fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)" }}>
            You can ask globally or choose a `work_id` to keep the answer grounded in one paper.
          </Typography>
        </Box>
      ) : null}

      {history.length > 0 ? (
        <Box
          sx={{
            mb: 2,
            p: 1.5,
            borderRadius: "6px",
            border: "1px solid rgba(255,255,255,0.08)",
            backgroundColor: "#1a1a1a",
          }}
        >
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.9)" }}>
            {standaloneMode ? "Recent questions" : "Recent workspace questions"}
          </Typography>
          <Box sx={{ mt: 1, display: "flex", flexDirection: "column", gap: 0.75 }}>
            {history.slice(0, 3).map((item) => (
              <Box key={item.id} sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                <Box sx={{ minWidth: 0 }}>
                  <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.82)" }}>{item.query}</Typography>
                  <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.25 }}>
                    {item.workId ? `${item.workId} · ` : "global corpus · "}
                    top_k {item.topK} · {item.citationCount} citations
                  </Typography>
                </Box>
                <CursorSmallButton
                  type="button"
                  onClick={() => {
                    setQuery(item.query);
                    if (!locked) setWorkId(item.workId);
                    setTopK(String(item.topK));
                  }}
                >
                  Restore
                </CursorSmallButton>
              </Box>
            ))}
          </Box>
        </Box>
      ) : null}

      {locked ? (
        <Box sx={{ mb: 2, p: 1.25, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#1a1a1a" }}>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>work_id (workspace scope)</Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)", fontFamily: "monospace", mt: 0.25 }}>
            {workId}
          </Typography>
        </Box>
      ) : null}

      <Box component="form" onSubmit={onSubmit} sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
        <TextField
          label="Query"
          value={query}
          onChange={(ev) => setQuery(ev.target.value)}
          multiline
          minRows={2}
          fullWidth
          size="small"
          sx={{
            "& .MuiInputBase-input": { fontSize: "0.8125rem" },
            "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
          }}
        />
        {!locked ? (
          <Autocomplete
            freeSolo
            options={workOptions}
            getOptionLabel={(opt) =>
              typeof opt === "string" ? opt : `${(opt.title || "").slice(0, 80) || opt.work_id} (${opt.work_id})`
            }
            inputValue={workId}
            onInputChange={(_e, v) => setWorkId(v)}
            onChange={(_e, opt) => {
              if (opt && typeof opt === "object" && opt.work_id) {
                setWorkId(String(opt.work_id));
              }
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="work_id (optional, pick from corpus)"
                size="small"
                sx={{
                  "& .MuiInputBase-input": { fontSize: "0.8125rem" },
                  "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
                }}
              />
            )}
          />
        ) : null}
        <TextField
          label="top_k"
          value={topK}
          onChange={(ev) => setTopK(ev.target.value)}
          fullWidth
          size="small"
          sx={{
            "& .MuiInputBase-input": { fontSize: "0.8125rem" },
            "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
          }}
        />
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
          <CursorPrimaryButton type="submit" disabled={loading}>
            {loading ? "Querying…" : "Run query"}
          </CursorPrimaryButton>
          {inWorkspace ? (
            <CursorSmallButton
              component={Link}
              to={buildStandaloneTracePath("/ask", workId)}
              sx={{ textDecoration: "none" }}
            >
              Open standalone Ask
            </CursorSmallButton>
          ) : null}
        </Box>
      </Box>

      {error ? (
        <Alert severity="error" sx={{ mt: 2, fontSize: "0.8125rem" }}>
          {error}
        </Alert>
      ) : null}

      {normalized ? (
        <Box
          sx={{
            mt: 2,
            p: 2,
            borderRadius: "6px",
            border: "1px solid rgba(255,255,255,0.08)",
            backgroundColor: "#1a1a1a",
          }}
        >
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 1 }}>Answer</Typography>
          <Typography sx={{ fontWeight: 600, fontSize: "0.75rem", color: "rgba(255,255,255,0.72)", mb: 0.5 }}>Why this answer</Typography>
          <Box component="ul" sx={{ m: 0, mb: 1.25, pl: 2.25, color: "rgba(255,255,255,0.62)", fontSize: "0.75rem", lineHeight: 1.5 }}>
            {buildAskAnswerRationale(normalized, { locked, inWorkspace, formWorkId: workId }).map((line, idx) => (
              <Box component="li" key={idx} sx={{ mb: 0.35 }}>
                {line}
              </Box>
            ))}
          </Box>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)", whiteSpace: "pre-wrap" }}>
            {normalized.answer || "—"}
          </Typography>

          {normalized.retrieval_trace.degraded.length > 0 || normalized.graph_context.degraded.length > 0 ? (
            <Alert severity="info" sx={{ mt: 1.5, fontSize: "0.8125rem", backgroundColor: "rgba(255,255,255,0.03)" }}>
              Some context had to degrade during retrieval. Review the trace details below before using this answer as a final conclusion.
            </Alert>
          ) : null}

          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.5 }}>Citations</Typography>
          {normalized.citations.length === 0 ? (
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>
              No supporting citations were returned for this answer.
            </Typography>
          ) : (
            normalized.citations.map((c, i) => {
              const wid = c.work_id != null ? String(c.work_id) : "";
              const chunkFingerprint = c.chunk_fingerprint != null ? String(c.chunk_fingerprint) : "";
              const sectionPath = c.section_path != null ? String(c.section_path) : "";
              const citationIndex = String(i + 1);
              const sameAsWorkspace = inWorkspace && wid && wid === String(workspaceWorkId).trim();
              return (
                <Box key={i} sx={{ mb: 1, fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)" }}>
                  <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.82)" }}>
                    Citation #{c.rank} · score {String(c.score)} · {wid || "no work context"}
                  </Typography>
                  <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.25 }}>
                    chunk {String(c.chunk_fingerprint ?? "—")}
                  </Typography>
                  {wid ? (
                    <Box sx={{ mt: 0.5, display: "flex", flexWrap: "wrap", gap: 1 }}>
                      {sameAsWorkspace ? (
                        <>
                          <Link
                            to={buildWorkspaceTracePath(wid, "reader", {
                              chunkFingerprint,
                              section: sectionPath,
                              citation: citationIndex,
                            })}
                            style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}
                          >
                            Open Reader
                          </Link>
                          <Link
                            to={buildWorkspaceTracePath(wid, "evidence", {
                              chunkFingerprint,
                              section: sectionPath,
                              citation: citationIndex,
                            })}
                            style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}
                          >
                            Open Evidence
                          </Link>
                          <Link
                            to={buildWorkspaceTracePath(wid, "graph", {
                              chunkFingerprint,
                              section: sectionPath,
                              citation: citationIndex,
                            })}
                            style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}
                          >
                            Open Graph
                          </Link>
                        </>
                      ) : (
                        <>
                          <Link
                            to={buildWorkspaceTracePath(wid, "reader", {
                              chunkFingerprint,
                              section: sectionPath,
                              citation: citationIndex,
                            })}
                            style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}
                          >
                            Open in Workspace
                          </Link>
                          <Link
                            to={buildStandaloneTracePath("/reader", wid, {
                              chunkFingerprint,
                              section: sectionPath,
                              citation: citationIndex,
                            })}
                            style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}
                          >
                            Standalone Reader
                          </Link>
                          <Link
                            to={buildStandaloneTracePath("/evidence", wid, {
                              chunkFingerprint,
                              section: sectionPath,
                              citation: citationIndex,
                            })}
                            style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}
                          >
                            Standalone Evidence
                          </Link>
                          <Link
                            to={buildStandaloneTracePath("/graph", wid, {
                              chunkFingerprint,
                              section: sectionPath,
                              citation: citationIndex,
                            })}
                            style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}
                          >
                            Standalone Graph
                          </Link>
                        </>
                      )}
                    </Box>
                  ) : null}
                  <Box component="span" sx={{ display: "block", color: "rgba(255,255,255,0.55)", mt: 0.25 }}>
                    {String(c.excerpt ?? "").slice(0, 280)}
                    {String(c.excerpt ?? "").length > 280 ? "…" : ""}
                  </Box>
                </Box>
              );
            })
          )}

          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.5 }}>Graph context</Typography>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)" }}>
            semantic_available={String(normalized.graph_context.semantic_available)} · context_work_id=
            {normalized.graph_context.context_work_id ?? "null"}
            {normalized.graph_context.error ? ` error=${normalized.graph_context.error}` : ""}
          </Typography>
          <FlagChips label="graph_context.degraded" items={normalized.graph_context.degraded} />
          <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 0.5 }}>
            {normalized.graph_context.methods.map((m) => (
              <Chip key={`m-${m}`} label={m} size="small" sx={{ height: 22, fontSize: "0.75rem" }} />
            ))}
            {normalized.graph_context.datasets.map((d) => (
              <Chip key={`d-${d}`} label={d} size="small" sx={{ height: 22, fontSize: "0.75rem" }} />
            ))}
          </Box>

          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.5 }}>Retrieval trace</Typography>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 0.75 }}>
            Summary of how evidence was retrieved. Expand advanced for the full JSON (embedding and low-level fields).
          </Typography>
          <Box sx={{ mb: 1 }}>
            {formatRetrievalSummaryLines(normalized.retrieval_trace).map((line, idx) => (
              <Typography key={idx} sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)", lineHeight: 1.45 }}>
                {line}
              </Typography>
            ))}
          </Box>
          <CursorSmallButton type="button" onClick={() => setRetrievalJsonOpen((v) => !v)} sx={{ mb: 1 }}>
            {retrievalJsonOpen ? "Hide advanced JSON" : "Show advanced JSON"}
          </CursorSmallButton>
          <Collapse in={retrievalJsonOpen} timeout="auto" unmountOnExit>
            <Typography
              component="pre"
              sx={{
                fontSize: "0.7rem",
                color: "rgba(255,255,255,0.5)",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                m: 0,
                p: 1,
                borderRadius: "6px",
                border: "1px solid rgba(255,255,255,0.08)",
                backgroundColor: "rgba(0,0,0,0.25)",
              }}
            >
              {JSON.stringify(
                {
                  qdrant_collection: normalized.retrieval_trace.qdrant_collection,
                  top_k_requested: normalized.retrieval_trace.top_k_requested,
                  citations_returned: normalized.retrieval_trace.citations_returned,
                  hit_count: normalized.retrieval_trace.hit_count,
                  retrieval_policy: normalized.retrieval_trace.retrieval_policy,
                  filter_work_id: normalized.retrieval_trace.filter_work_id,
                  resolved_work_id: normalized.retrieval_trace.resolved_work_id,
                  embedding: normalized.retrieval_trace.embedding,
                  degraded: normalized.retrieval_trace.degraded,
                },
                null,
                2,
              )}
            </Typography>
          </Collapse>
        </Box>
      ) : null}
    </Box>
  );
}
