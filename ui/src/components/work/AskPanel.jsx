import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Alert from "@mui/material/Alert";
import Chip from "@mui/material/Chip";
import Autocomplete from "@mui/material/Autocomplete";

import { CursorPrimaryButton, CursorSmallButton } from "../common/index.js";
import {
  buildQueryBody,
  getWorks,
  normalizeQueryResponse,
  postQuery,
} from "../../services/researchApi.js";
import { buildWorkspacePath, persistWorkId } from "../../pages/WorkspacePage/utils/workContext.js";

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

  useEffect(() => {
    if (locked) {
      setWorkId(String(scopedWorkId).trim());
    } else {
      setWorkId(initialWorkId || "");
    }
  }, [locked, scopedWorkId, initialWorkId]);

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
    try {
      const res = await postQuery(bodyPreview);
      setNormalized(normalizeQueryResponse(res.data));
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
        <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem", mb: 2 }}>
          Question is scoped to the active work. Citations link to Reader / Evidence inside this workspace.
        </Typography>
      )}

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
              to={`/ask?work_id=${encodeURIComponent(workId)}`}
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
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)", whiteSpace: "pre-wrap" }}>
            {normalized.answer || "—"}
          </Typography>

          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.5 }}>Citations</Typography>
          {normalized.citations.length === 0 ? (
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>None</Typography>
          ) : (
            normalized.citations.map((c, i) => {
              const wid = c.work_id != null ? String(c.work_id) : "";
              const sameAsWorkspace = inWorkspace && wid && wid === String(workspaceWorkId).trim();
              return (
                <Box key={i} sx={{ mb: 1, fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)" }}>
                  #{c.rank} score={String(c.score)} work_id={wid || "—"} fp={String(c.chunk_fingerprint ?? "—")}
                  {wid ? (
                    <Box sx={{ mt: 0.5, display: "flex", flexWrap: "wrap", gap: 1 }}>
                      {sameAsWorkspace ? (
                        <>
                          <Link
                            to={buildWorkspacePath(wid, "reader")}
                            style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}
                          >
                            Reader (workspace)
                          </Link>
                          <Link
                            to={buildWorkspacePath(wid, "evidence")}
                            style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}
                          >
                            Evidence (workspace)
                          </Link>
                          <Link
                            to={buildWorkspacePath(wid, "graph")}
                            style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}
                          >
                            Graph (workspace)
                          </Link>
                        </>
                      ) : (
                        <>
                          <Link
                            to={buildWorkspacePath(wid, "reader")}
                            style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}
                          >
                            Workspace
                          </Link>
                          <Link
                            to={`/reader?work_id=${encodeURIComponent(wid)}`}
                            style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}
                          >
                            Reader
                          </Link>
                          <Link
                            to={`/evidence?work_id=${encodeURIComponent(wid)}`}
                            style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}
                          >
                            Evidence
                          </Link>
                          <Link
                            to={`/graph?work_id=${encodeURIComponent(wid)}`}
                            style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}
                          >
                            Graph
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
            semantic_available={String(normalized.graph_context.semantic_available)} context_work_id=
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
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)", whiteSpace: "pre-wrap" }}>
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
        </Box>
      ) : null}
    </Box>
  );
}
