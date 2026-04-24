import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Alert from "@mui/material/Alert";
import Chip from "@mui/material/Chip";
import Autocomplete from "@mui/material/Autocomplete";
import Collapse from "@mui/material/Collapse";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Switch from "@mui/material/Switch";

import { CursorPrimaryButton, CursorSmallButton } from "../common/index.js";
import WorkIdGlossaryHint from "../layout/WorkIdGlossaryHint.jsx";
import {
  buildAskAnswerRationale,
  buildQueryBody,
  createAskSession as createAskSessionRequest,
  formatResearchApiError,
  formatRetrievalSummaryLines,
  getWorks,
  listAskSessions as listAskSessionsRequest,
  normalizeQueryResponse,
  patchAskSession as patchAskSessionRequest,
  postQuery,
} from "../../services/researchApi.js";
import {
  apiSessionsToBundle,
  entriesToApiTurns,
  isServerAskSessionId,
  readAskServerSyncPref,
  writeAskServerSyncPref,
} from "./askSessionServerBridge.js";
import { rememberAskHistory } from "./askHistoryState.js";
import {
  appendAskSessionTurn,
  createAskSession,
  deriveAskScopeKey,
  getActiveSessionEntries,
  migrateLegacyAskHistoryToSessions,
  readAskSessionUi,
  renameAskSession,
  replaceScopeBundle,
  sessionExistsInScope,
  setActiveAskSession,
} from "./askSessionState.js";
import { buildStandaloneTracePath, buildWorkspaceTracePath } from "./traceabilityState.js";
import { persistWorkId } from "../../pages/WorkspacePage/utils/workContext.js";
import { useI18n } from "../../i18n/I18nContext.jsx";

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
 *   workspaceId?: string,
 *   urlSessionId?: string,
 *   onUrlSessionIdChange?: (sessionId: string) => void,
 * }} props
 */
export default function AskPanel({
  scopedWorkId = null,
  initialWorkId = "",
  showPageChrome = true,
  workspaceWorkId = null,
  workspaceId = "",
  urlSessionId = "",
  onUrlSessionIdChange,
}) {
  const { t } = useI18n();
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
  const [sessionTick, setSessionTick] = useState(0);
  const [sessionTitleDraft, setSessionTitleDraft] = useState("");
  const [serverSync, setServerSync] = useState(() => readAskServerSyncPref());

  const scopeKey = useMemo(
    () => deriveAskScopeKey({ locked, scopedWorkId, workspaceId }),
    [locked, scopedWorkId, workspaceId],
  );

  const bumpSessions = useCallback(() => {
    setSessionTick((t) => t + 1);
  }, []);

  const { activeId: activeSessionId, sessions: sessionList } = readAskSessionUi(scopeKey, sessionTick);

  const activeSessionMeta = useMemo(
    () => sessionList.find((s) => s.id === activeSessionId),
    [sessionList, activeSessionId],
  );

  useEffect(() => {
    setSessionTitleDraft(activeSessionMeta?.title || "");
  }, [activeSessionMeta?.title, activeSessionId]);

  useEffect(() => {
    const id = String(urlSessionId || "").trim();
    if (!id) return;
    if (!sessionExistsInScope(scopeKey, id)) return;
    const { activeId } = readAskSessionUi(scopeKey, sessionTick);
    if (activeId !== id) {
      setActiveAskSession(scopeKey, id);
      bumpSessions();
    }
  }, [urlSessionId, scopeKey, bumpSessions, sessionTick]);

  useEffect(() => {
    if (locked) {
      setWorkId(String(scopedWorkId).trim());
    } else {
      setWorkId(initialWorkId || "");
    }
  }, [locked, scopedWorkId, initialWorkId]);

  useEffect(() => {
    migrateLegacyAskHistoryToSessions(scopeKey, (item) => {
      if (locked) return String(item.workId || "").trim() === String(scopedWorkId || "").trim();
      return true;
    });
    getActiveSessionEntries(scopeKey);
    bumpSessions();
  }, [scopeKey, locked, scopedWorkId, bumpSessions]);

  useEffect(() => {
    if (!serverSync) return undefined;
    let cancelled = false;
    (async () => {
      try {
        const res = await listAskSessionsRequest(scopeKey);
        if (cancelled) return;
        replaceScopeBundle(scopeKey, apiSessionsToBundle(res.data));
        bumpSessions();
      } catch (err) {
        if (!cancelled) setError(formatResearchApiError(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [serverSync, scopeKey, bumpSessions]);

  useEffect(() => {
    setHistory(getActiveSessionEntries(scopeKey));
  }, [scopeKey, sessionTick]);

  useEffect(() => {
    if (locked || initialWorkId) return;
    const recent = getActiveSessionEntries(scopeKey);
    if (recent[0]) {
      setQuery(recent[0].query);
      setWorkId(recent[0].workId);
      setTopK(String(recent[0].topK || 5));
    }
  }, [locked, initialWorkId, scopeKey]);

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

  const bodyPreview = useMemo(() => buildQueryBody(query, workId, topK, workspaceId), [query, workId, topK, workspaceId]);

  const inWorkspace = Boolean(workspaceWorkId && String(workspaceWorkId).trim());
  const corpusWorkspaceOnly = Boolean(
    String(workspaceId || "").trim() && !String(workId || "").trim() && !locked,
  );
  const standaloneMode = !inWorkspace && !locked && !corpusWorkspaceOnly;

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
      const queryMode =
        locked || inWorkspace ? "workspace" : corpusWorkspaceOnly ? "workspace_corpus" : workId ? "scoped" : "global";
      rememberAskHistory({
        query,
        workId,
        topK,
        answer: nextNormalized.answer,
        citationCount: nextNormalized.citations.length,
        mode: queryMode,
      });
      appendAskSessionTurn(scopeKey, {
        query,
        workId,
        topK,
        answer: nextNormalized.answer,
        citationCount: nextNormalized.citations.length,
        mode: queryMode,
      });
      bumpSessions();
      if (serverSync) {
        const { activeId: sid } = readAskSessionUi(scopeKey);
        if (sid && isServerAskSessionId(sid)) {
          try {
            await patchAskSessionRequest(scopeKey, sid, {
              turns: entriesToApiTurns(getActiveSessionEntries(scopeKey)),
              active: true,
            });
          } catch {
            /* non-fatal */
          }
        }
      }
    } catch (err) {
      setError(formatResearchApiError(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!locked && workId.trim()) {
      persistWorkId(workId);
    }
  }, [locked, workId]);

  return (
    <Box sx={{ width: "100%", boxSizing: "border-box" }}>
      {showPageChrome ? (
        <>
          <Typography sx={{ fontWeight: 600, mb: 1, color: "rgba(255,255,255,0.9)" }}>{t("askPanel.chromeTitle")}</Typography>
          <Typography sx={{ color: "rgba(255,255,255,0.6)", fontSize: "0.8125rem", mb: 2 }}>
            {t("askPanel.chrome.p1")}
            <code style={{ color: "rgba(129,140,248,0.95)" }}>VITE_API_BASE_URL</code>
            {t("askPanel.chrome.p2")}
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
            {inWorkspace || locked
              ? t("askPanel.banner.workspaceScoped")
              : corpusWorkspaceOnly
                ? t("askPanel.banner.workspaceCorpusTitle")
                : t("askPanel.banner.standalone")}
          </Typography>
          <Typography sx={{ color: "rgba(255,255,255,0.78)", fontSize: "0.8125rem" }}>
            {inWorkspace || locked
              ? t("askPanel.banner.descWorkspace")
              : corpusWorkspaceOnly
                ? t("askPanel.banner.descWorkspaceCorpus")
                : t("askPanel.banner.descStandalone")}
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
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)" }}>
            {t("askPanel.optionalContext.title")}
          </Typography>
          <Typography sx={{ mt: 0.6, fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)" }}>
            <WorkIdGlossaryHint variant="ask" />
          </Typography>
        </Box>
      ) : null}

      <Box
        sx={{
          mb: 2,
          p: 1.5,
          borderRadius: "6px",
          border: "1px solid rgba(255,255,255,0.08)",
          backgroundColor: "#1a1a1a",
        }}
      >
        <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.9)" }}>{t("askPanel.session.title")}</Typography>
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.35, mb: 1 }}>
          {standaloneMode ? t("askPanel.session.hintStandalone") : t("askPanel.session.hintWorkspace")}
          {serverSync ? (
            <Box component="span" sx={{ display: "block", mt: 0.5 }}>
              {t("askPanel.session.serverSyncLine")}
            </Box>
          ) : null}
          {onUrlSessionIdChange ? (
            <Box component="span" sx={{ display: "block", mt: 0.5 }}>
              {t("askPanel.session.urlLine")}
            </Box>
          ) : null}
        </Typography>
        <FormControlLabel
          sx={{ mb: 1, "& .MuiFormControlLabel-label": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.7)" } }}
          control={
            <Switch
              size="small"
              checked={serverSync}
              onChange={(_e, v) => {
                writeAskServerSyncPref(v);
                setServerSync(v);
              }}
            />
          }
          label={t("askPanel.serverSyncLabel")}
        />
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "flex-end" }}>
          <FormControl size="small" sx={{ minWidth: 200, flex: "1 1 180px" }}>
            <InputLabel id="ask-session-select-label">{t("askPanel.session.selectLabel")}</InputLabel>
            <Select
              labelId="ask-session-select-label"
              label={t("askPanel.session.selectLabel")}
              value={activeSessionId || ""}
              onChange={async (e) => {
                const v = String(e.target.value);
                setActiveAskSession(scopeKey, v);
                bumpSessions();
                onUrlSessionIdChange?.(v);
                if (serverSync && v && isServerAskSessionId(v)) {
                  try {
                    await patchAskSessionRequest(scopeKey, v, { active: true });
                  } catch {
                    /* non-fatal */
                  }
                }
              }}
              sx={{ fontSize: "0.8125rem" }}
            >
              {sessionList.map((s) => (
                <MenuItem key={s.id} value={s.id} sx={{ fontSize: "0.8125rem" }}>
                  {s.title}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            label={t("askPanel.sessionTitle")}
            value={sessionTitleDraft}
            onChange={(ev) => setSessionTitleDraft(ev.target.value)}
            onBlur={async () => {
              const next = sessionTitleDraft.trim();
              if (activeSessionId && next && next !== (activeSessionMeta?.title || "").trim()) {
                renameAskSession(scopeKey, activeSessionId, next);
                bumpSessions();
                if (serverSync && isServerAskSessionId(activeSessionId)) {
                  try {
                    await patchAskSessionRequest(scopeKey, activeSessionId, { title: next, active: true });
                  } catch {
                    /* non-fatal */
                  }
                }
              }
            }}
            size="small"
            sx={{
              flex: "2 1 220px",
              "& .MuiInputBase-input": { fontSize: "0.8125rem" },
              "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
            }}
          />
          <CursorSmallButton
            type="button"
            onClick={async () => {
              if (serverSync) {
                try {
                  await createAskSessionRequest(scopeKey, {});
                  const res = await listAskSessionsRequest(scopeKey);
                  replaceScopeBundle(scopeKey, apiSessionsToBundle(res.data));
                  bumpSessions();
                  const aid = res.data?.active_session_id;
                  if (aid) onUrlSessionIdChange?.(String(aid));
                } catch (err) {
                  setError(formatResearchApiError(err));
                }
                return;
              }
              const id = createAskSession(scopeKey);
              bumpSessions();
              if (id) onUrlSessionIdChange?.(id);
            }}
          >
            {t("askPanel.newSession")}
          </CursorSmallButton>
        </Box>
      </Box>

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
            {standaloneMode ? t("askPanel.recent.standalone") : t("askPanel.recent.workspace")}
          </Typography>
          <Box sx={{ mt: 1, display: "flex", flexDirection: "column", gap: 0.75 }}>
            {history.slice(0, 3).map((item) => (
              <Box key={item.id} sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                <Box sx={{ minWidth: 0 }}>
                  <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.82)" }}>{item.query}</Typography>
                  <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.25 }}>
                    {item.workId ? `${item.workId} · ` : t("askPanel.recent.globalLine")}
                    {t("askPanel.recent.topK", { k: String(item.topK), count: String(item.citationCount) })}
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
                  {t("askPanel.restore")}
                </CursorSmallButton>
              </Box>
            ))}
          </Box>
        </Box>
      ) : (
        <Box
          sx={{
            mb: 2,
            p: 1.5,
            borderRadius: "6px",
            border: "1px dashed rgba(255,255,255,0.1)",
            backgroundColor: "rgba(255,255,255,0.02)",
          }}
        >
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)" }}>{t("askPanel.noTurns.title")}</Typography>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.5 }}>{t("askPanel.noTurns.body")}</Typography>
        </Box>
      )}

      {locked ? (
        <Box sx={{ mb: 2, p: 1.25, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#1a1a1a" }}>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>{t("askPanel.workIdScopeLabel")}</Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)", fontFamily: "monospace", mt: 0.25 }}>
            {workId}
          </Typography>
        </Box>
      ) : null}

      <Box component="form" onSubmit={onSubmit} sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
        <TextField
          label={t("askPanel.query")}
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
                label={t("askPanel.workIdAutocomplete")}
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
          label={t("askPanel.topK")}
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
            {loading ? t("askPanel.runQueryLoading") : t("askPanel.runQuery")}
          </CursorPrimaryButton>
          {inWorkspace ? (
            <CursorSmallButton
              component={Link}
              to={buildStandaloneTracePath("/ask", workId)}
              sx={{ textDecoration: "none" }}
            >
              {t("askPanel.openStandaloneAsk")}
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
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 1 }}>{t("askPanel.answer.title")}</Typography>
          <Typography sx={{ fontWeight: 600, fontSize: "0.75rem", color: "rgba(255,255,255,0.72)", mb: 0.5 }}>{t("askPanel.answer.why")}</Typography>
          <Box component="ul" sx={{ m: 0, mb: 1.25, pl: 2.25, color: "rgba(255,255,255,0.62)", fontSize: "0.75rem", lineHeight: 1.5 }}>
            {buildAskAnswerRationale(normalized, { locked, inWorkspace, formWorkId: workId }).map((line, idx) => (
              <Box component="li" key={idx} sx={{ mb: 0.35 }}>
                {line}
              </Box>
            ))}
          </Box>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)", whiteSpace: "pre-wrap" }}>
            {normalized.answer || t("workspace.upload.dash")}
          </Typography>

          {normalized.retrieval_trace.degraded.length > 0 || normalized.graph_context.degraded.length > 0 ? (
            <Alert severity="info" sx={{ mt: 1.5, fontSize: "0.8125rem", backgroundColor: "rgba(255,255,255,0.03)" }}>
              {t("askPanel.answer.degraded")}
            </Alert>
          ) : null}

          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.5 }}>{t("askPanel.citations.title")}</Typography>
          {normalized.citations.length === 0 ? (
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("askPanel.citations.none")}</Typography>
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
                    {t("askPanel.citation.line", {
                      rank: String(c.rank),
                      score: String(c.score),
                      work: wid || t("askPanel.citation.noWork"),
                    })}
                  </Typography>
                  <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.25 }}>
                    {t("askPanel.chunkLabel")} {String(c.chunk_fingerprint ?? t("workspace.upload.dash"))}
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
                            {t("askPanel.openReader")}
                          </Link>
                          <Link
                            to={buildWorkspaceTracePath(wid, "evidence", {
                              chunkFingerprint,
                              section: sectionPath,
                              citation: citationIndex,
                            })}
                            style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}
                          >
                            {t("askPanel.openEvidence")}
                          </Link>
                          <Link
                            to={buildWorkspaceTracePath(wid, "graph", {
                              chunkFingerprint,
                              section: sectionPath,
                              citation: citationIndex,
                            })}
                            style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}
                          >
                            {t("askPanel.openGraph")}
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
                            {t("askPanel.openInWorkspace")}
                          </Link>
                          <Link
                            to={buildStandaloneTracePath("/reader", wid, {
                              chunkFingerprint,
                              section: sectionPath,
                              citation: citationIndex,
                            })}
                            style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}
                          >
                            {t("askPanel.standaloneReader")}
                          </Link>
                          <Link
                            to={buildStandaloneTracePath("/evidence", wid, {
                              chunkFingerprint,
                              section: sectionPath,
                              citation: citationIndex,
                            })}
                            style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}
                          >
                            {t("askPanel.standaloneEvidence")}
                          </Link>
                          <Link
                            to={buildStandaloneTracePath("/graph", wid, {
                              chunkFingerprint,
                              section: sectionPath,
                              citation: citationIndex,
                            })}
                            style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}
                          >
                            {t("askPanel.standaloneGraph")}
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

          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.5 }}>{t("askPanel.graphContext.title")}</Typography>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)" }}>
            {t("askPanel.graphContext.body", {
              semantic: String(normalized.graph_context.semantic_available),
              ctx: String(normalized.graph_context.context_work_id ?? "null"),
              err: normalized.graph_context.error ? ` error=${normalized.graph_context.error}` : "",
            })}
          </Typography>
          <FlagChips label={t("askPanel.flag.graphDegraded")} items={normalized.graph_context.degraded} />
          <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 0.5 }}>
            {normalized.graph_context.methods.map((m) => (
              <Chip key={`m-${m}`} label={m} size="small" sx={{ height: 22, fontSize: "0.75rem" }} />
            ))}
            {normalized.graph_context.datasets.map((d) => (
              <Chip key={`d-${d}`} label={d} size="small" sx={{ height: 22, fontSize: "0.75rem" }} />
            ))}
          </Box>

          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.5 }}>{t("askPanel.retrieval.title")}</Typography>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 0.75 }}>{t("askPanel.retrieval.summary")}</Typography>
          <Box sx={{ mb: 1 }}>
            {formatRetrievalSummaryLines(normalized.retrieval_trace).map((line, idx) => (
              <Typography key={idx} sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)", lineHeight: 1.45 }}>
                {line}
              </Typography>
            ))}
          </Box>
          <CursorSmallButton type="button" onClick={() => setRetrievalJsonOpen((v) => !v)} sx={{ mb: 1 }}>
            {retrievalJsonOpen ? t("askPanel.toggleJson.hide") : t("askPanel.toggleJson.show")}
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
