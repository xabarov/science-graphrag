import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import BarChartOutlinedIcon from "@mui/icons-material/BarChartOutlined";
import ContentCopyOutlinedIcon from "@mui/icons-material/ContentCopyOutlined";
import DeleteOutlineOutlinedIcon from "@mui/icons-material/DeleteOutlineOutlined";
import KeyboardArrowDownRoundedIcon from "@mui/icons-material/KeyboardArrowDownRounded";
import ReplayOutlinedIcon from "@mui/icons-material/ReplayOutlined";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorIconAction } from "../common/index.js";
import { useFeedback } from "../feedback/index.js";
import { AskAnswerPanel } from "./AskAnswerPanel.jsx";
import { AgentAssistantTurnShell } from "./AgentAssistantTurnShell.jsx";
import { AgentRunHeader } from "./AgentRunHeader.jsx";
import { AgentLiveStatus } from "./AgentLiveStatus.jsx";
import MarkdownView from "./MarkdownView.jsx";

const SCROLL_BOTTOM_THRESHOLD_PX = 80;

function toFiniteNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function pickNumber(...vals) {
  for (const v of vals) {
    const n = toFiniteNumber(v);
    if (n != null) return n;
  }
  return null;
}

function formatMetricValue(value, { unit = "", digits = 0 } = {}) {
  const n = toFiniteNumber(value);
  if (n == null) return "—";
  return `${n.toLocaleString(undefined, { maximumFractionDigits: digits })}${unit}`;
}

function extractTurnMetadata(entry) {
  const details = entry?.details && typeof entry.details === "object" ? entry.details : {};
  const runMeta = details.run_metadata && typeof details.run_metadata === "object" ? details.run_metadata : {};
  const usage = runMeta.usage && typeof runMeta.usage === "object" ? runMeta.usage : {};
  const promptTokens = pickNumber(usage.prompt_tokens, usage.input_tokens, runMeta.prompt_tokens);
  const completionTokens = pickNumber(usage.completion_tokens, usage.output_tokens, runMeta.completion_tokens);
  const totalTokens = pickNumber(
    usage.total_tokens,
    runMeta.total_tokens,
    runMeta.token_count,
    promptTokens != null && completionTokens != null ? promptTokens + completionTokens : null,
  );
  const durationMs = pickNumber(details.duration_ms, runMeta.duration_ms);
  const tokensPerSecond = pickNumber(usage.tokens_per_second, usage.tps, runMeta.tokens_per_second, runMeta.tps);
  const costUsd = pickNumber(usage.cost_usd, usage.usd_cost, runMeta.cost_usd, runMeta.usd_cost);
  const eventsCount = Array.isArray(details.stream_events) ? details.stream_events.length : 0;
  const citationCount = Array.isArray(details.citations) ? details.citations.length : pickNumber(entry?.citationCount) || 0;
  const answerClass = String(details.answer_class || "").trim();
  return {
    durationMs,
    totalTokens,
    promptTokens,
    completionTokens,
    tokensPerSecond,
    costUsd,
    eventsCount,
    citationCount,
    answerClass,
  };
}

function ChatUserBubble({ text }) {
  const tk = useTheme().appTokens;
  return (
    <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1.5 }}>
      <Box
        sx={{
          maxWidth: "min(720px, 92%)",
          px: 1.25,
          py: 1,
          borderRadius: "6px",
          backgroundColor: tk.accent.chipReadyBg,
          border: `1px solid ${tk.accent.softBorder}`,
        }}
      >
        <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, whiteSpace: "pre-wrap" }}>{text}</Typography>
      </Box>
    </Box>
  );
}

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   scopeKey: string,
 *   activeSessionId: string | null,
 *   streamingTarget: { scopeKey: string, sessionId: string } | null,
 *   history: Array<{
 *     id: string,
 *     query: string,
 *     workId?: string,
 *     answer?: string,
 *     details?: Record<string, unknown> | null,
 *   }>,
 *   pendingUserQuery: string,
 *   isLoading: boolean,
 *   streamEvents: unknown[],
 *   liveNormalized: unknown | null,
 *   locked: boolean,
 *   inWorkspace: boolean,
 *   workId: string,
 *   workspaceWorkId: string | null,
 *   agentToolTrace: unknown[],
 *   retrievalJsonOpen: boolean,
 *   onToggleRetrievalJson: () => void,
 *   starterPromptKeys?: string[],
 *   onStarterPrompt?: (text: string) => void,
 *   onRestartFromTurn?: (turnId: string) => void | Promise<void>,
 *   onCopyAssistantEntry?: (entry: unknown) => void | Promise<void>,
 *   onDeleteTurn?: (turnId: string) => void | Promise<void>,
 *   restartDisabled?: boolean,
 *   deleteDisabled?: boolean,
 * }} props
 */
export function ChatMessageThread({
  t,
  scopeKey,
  activeSessionId,
  streamingTarget,
  history,
  pendingUserQuery,
  isLoading,
  streamEvents,
  liveNormalized,
  locked,
  inWorkspace,
  workId,
  workspaceWorkId,
  agentToolTrace,
  retrievalJsonOpen,
  onToggleRetrievalJson,
  starterPromptKeys = [],
  onStarterPrompt,
  onRestartFromTurn,
  onCopyAssistantEntry,
  onDeleteTurn,
  restartDisabled = false,
  deleteDisabled = false,
}) {
  const { confirm } = useFeedback();
  const tk = useTheme().appTokens;
  const chronological = useMemo(() => [...history].reverse(), [history]);
  const streamForThisChat = Boolean(
    streamingTarget &&
      streamingTarget.scopeKey === scopeKey &&
      String(streamingTarget.sessionId || "") === String(activeSessionId || ""),
  );
  // Include liveNormalized so a frame where pending cleared but history state has not yet
  // caught up (AskPanel batching) does not flash the empty-state over a completed answer.
  const hasThreadContent =
    chronological.length > 0 ||
    (Boolean(pendingUserQuery) && streamForThisChat) ||
    (Boolean(liveNormalized) && streamForThisChat);
  const showEmptyState = !hasThreadContent;

  const containerRef = useRef(null);
  const endRef = useRef(null);
  const [stickToBottom, setStickToBottom] = useState(true);
  /** Synchronous pin: must match scroll intent before useLayoutEffect runs (state can lag one frame). */
  const stickToBottomRef = useRef(true);

  const updateStickFromScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
    const stick = dist < SCROLL_BOTTOM_THRESHOLD_PX;
    stickToBottomRef.current = stick;
    setStickToBottom(stick);
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return undefined;
    el.addEventListener("scroll", updateStickFromScroll, { passive: true });
    return () => el.removeEventListener("scroll", updateStickFromScroll);
  }, [updateStickFromScroll]);

  const scrollContainerToBottom = useCallback((behavior = "auto") => {
    const el = containerRef.current;
    if (!el) return;
    const top = el.scrollHeight - el.clientHeight;
    if (behavior === "smooth") {
      el.scrollTo({ top, behavior: "smooth" });
    } else {
      el.scrollTop = top;
    }
  }, []);

  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    if (!stickToBottomRef.current) return;
    scrollContainerToBottom("auto");
  }, [
    scrollContainerToBottom,
    chronological.length,
    pendingUserQuery,
    isLoading,
    liveNormalized,
    streamEvents,
    streamForThisChat,
  ]);

  const showJump = hasThreadContent && !stickToBottom;
  const [metaEntry, setMetaEntry] = useState(null);
  const meta = useMemo(() => extractTurnMetadata(metaEntry), [metaEntry]);
  const maxMetaBar = useMemo(() => {
    const vals = [meta.durationMs, meta.totalTokens, meta.tokensPerSecond, meta.costUsd].map((v) => (v == null ? 0 : Math.abs(v)));
    return Math.max(...vals, 1);
  }, [meta]);

  return (
    <Box
      ref={containerRef}
      sx={{
        flex: 1,
        minHeight: 0,
        overflowY: showEmptyState ? "hidden" : "auto",
        pr: 0.5,
        display: "flex",
        flexDirection: "column",
        gap: 0,
        position: "relative",
        /*
         * Keep messages in normal document flow. `justifyContent: flex-end` inside an
         * overflow container can lay tall threads above the viewport with no usable
         * scroll range (messages exist in DOM but are visually invisible).
         */
        justifyContent: "flex-start",
        alignItems: showEmptyState ? "center" : "stretch",
      }}
    >
      {showEmptyState ? (
        <Box
          sx={{
            pb: 1.25,
            width: "100%",
            maxWidth: "min(920px, 100%)",
            mx: "auto",
          }}
        >
          <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: tk.text.primary, mb: 0.5 }}>{t("chat.thread.emptyTitle")}</Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted, mb: 1.25, lineHeight: 1.45 }}>{t("chat.thread.emptySubtitle")}</Typography>
          {starterPromptKeys.length > 0 && onStarterPrompt ? (
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
              {starterPromptKeys.map((key) => (
                <Chip
                  key={key}
                  size="small"
                  label={t(key)}
                  onClick={() => onStarterPrompt(t(key))}
                  sx={{
                    height: 26,
                    borderRadius: "6px",
                    border: `1px solid ${tk.border.strong}`,
                    backgroundColor: tk.surface.subtle,
                    color: tk.text.primary,
                    fontSize: "0.75rem",
                    maxWidth: "100%",
                    "& .MuiChip-label": { px: 1, whiteSpace: "normal", textAlign: "left" },
                    "&:hover": { backgroundColor: tk.accent.chipReadyBg, borderColor: tk.accent.softBorder },
                  }}
                />
              ))}
            </Box>
          ) : null}
        </Box>
      ) : null}

      {chronological.map((entry) => (
        <Box
          key={entry.id}
          sx={{
            mb: 2.25,
            "& .turn-actions": {
              opacity: 0,
              transform: "translateY(-2px)",
              transition: "opacity 0.15s ease, transform 0.15s ease",
            },
            "&:hover .turn-actions, &:focus-within .turn-actions": {
              opacity: 1,
              transform: "translateY(0)",
            },
            "@media (hover: none)": {
              "& .turn-actions": { opacity: 1, transform: "none" },
            },
          }}
        >
          <ChatUserBubble text={entry.query} />
          <Box sx={{ display: "flex", justifyContent: "flex-start" }}>
            <Box sx={{ position: "relative", width: "100%", maxWidth: "min(880px, 100%)" }}>
              {entry.details && typeof entry.details === "object" ? (
                <AgentAssistantTurnShell sx={{ mt: 1 }}>
                  <AskAnswerPanel
                    t={t}
                    normalized={entry.details}
                    locked={locked}
                    inWorkspace={inWorkspace}
                    workId={entry.workId || workId}
                    workspaceWorkId={workspaceWorkId}
                    retrievalMode="agent"
                    agentToolTrace={
                      Array.isArray(entry.details?.agent_tool_trace) ? entry.details.agent_tool_trace : []
                    }
                    retrievalJsonOpen={false}
                    onToggleRetrievalJson={() => {}}
                    streamEvents={
                      Array.isArray(entry.details?.stream_events) ? entry.details.stream_events : []
                    }
                    isRunActive={false}
                  />
                </AgentAssistantTurnShell>
              ) : (
                <AgentAssistantTurnShell sx={{ mt: 1 }}>
                  {String(entry.answer || "").trim() ? (
                    <Box
                      sx={{
                        "& .reader-markdown": {
                          fontSize: "0.8125rem",
                          lineHeight: 1.6,
                        },
                        "& .reader-markdown p:last-of-type": {
                          mb: 0,
                        },
                      }}
                    >
                      <MarkdownView markdown={String(entry.answer)} />
                    </Box>
                  ) : (
                    <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, whiteSpace: "pre-wrap" }}>—</Typography>
                  )}
                </AgentAssistantTurnShell>
              )}
              <Box className="turn-actions" sx={{ mt: 0.6, display: "flex", alignItems: "center", gap: 0.35 }}>
                <CursorIconAction
                  type="button"
                  disabled={restartDisabled}
                  aria-label={t("chat.thread.actions.retryAria")}
                  title={t("chat.thread.actions.retryAria")}
                  onClick={() => void onRestartFromTurn?.(entry.id)}
                >
                  <ReplayOutlinedIcon sx={{ fontSize: "1rem" }} />
                </CursorIconAction>
                <CursorIconAction
                  type="button"
                  aria-label={t("chat.thread.actions.copyAria")}
                  title={t("chat.thread.actions.copyAria")}
                  onClick={() => void onCopyAssistantEntry?.(entry)}
                >
                  <ContentCopyOutlinedIcon sx={{ fontSize: "1rem" }} />
                </CursorIconAction>
                <CursorIconAction
                  type="button"
                  aria-label={t("chat.thread.actions.metadataAria")}
                  title={t("chat.thread.actions.metadataAria")}
                  onClick={() => setMetaEntry(entry)}
                >
                  <BarChartOutlinedIcon sx={{ fontSize: "1rem" }} />
                </CursorIconAction>
                <CursorIconAction
                  type="button"
                  disabled={deleteDisabled}
                  aria-label={t("chat.thread.actions.deleteAria")}
                  title={t("chat.thread.actions.deleteAria")}
                  onClick={async () => {
                    const ok = await confirm({
                      title: t("chat.thread.deleteTurnDialogTitle"),
                      body: t("chat.thread.deleteTurnConfirm"),
                      variant: "danger",
                      confirmLabel: t("chat.sidebar.deleteConfirmButton"),
                      cancelLabel: t("chat.clear.cancel"),
                    });
                    if (!ok) return;
                    void onDeleteTurn?.(entry.id);
                  }}
                >
                  <DeleteOutlineOutlinedIcon sx={{ fontSize: "1rem" }} />
                </CursorIconAction>
              </Box>
            </Box>
          </Box>
        </Box>
      ))}

      {pendingUserQuery && streamForThisChat ? (
        <Box sx={{ mb: 2.25 }}>
          <ChatUserBubble text={pendingUserQuery} />
          <Box sx={{ display: "flex", justifyContent: "flex-start", pl: 0.5 }}>
            <Box sx={{ minWidth: 0, maxWidth: "min(880px, 100%)" }}>
              {liveNormalized ? (
                <AgentAssistantTurnShell sx={{ mt: 1 }}>
                  <AskAnswerPanel
                    t={t}
                    normalized={liveNormalized}
                    locked={locked}
                    inWorkspace={inWorkspace}
                    workId={workId}
                    workspaceWorkId={workspaceWorkId}
                    retrievalMode="agent"
                    agentToolTrace={agentToolTrace}
                    retrievalJsonOpen={retrievalJsonOpen}
                    onToggleRetrievalJson={onToggleRetrievalJson}
                    streamEvents={streamEvents}
                    isRunActive={isLoading}
                  />
                </AgentAssistantTurnShell>
              ) : isLoading ? (
                <AgentAssistantTurnShell sx={{ mt: 1 }}>
                  <AgentRunHeader
                    t={t}
                    runState="running"
                    answerClass={null}
                    citationCount={0}
                    durationMs={null}
                    streamEventCount={Array.isArray(streamEvents) ? streamEvents.length : 0}
                  />
                  <AgentLiveStatus t={t} streamEvents={streamEvents} isActive />
                </AgentAssistantTurnShell>
              ) : null}
            </Box>
          </Box>
        </Box>
      ) : null}

      <Dialog
        open={Boolean(metaEntry)}
        onClose={() => setMetaEntry(null)}
        slotProps={{
          paper: {
            sx: {
              backgroundColor: tk.surface.panel,
              border: `1px solid ${tk.border.default}`,
              borderRadius: "6px",
              minWidth: { xs: 300, sm: 420 },
            },
          },
        }}
      >
        <DialogTitle sx={{ fontSize: "0.9rem", color: tk.text.primary }}>{t("chat.thread.meta.title")}</DialogTitle>
        <DialogContent sx={{ pt: "8px !important" }}>
          <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1 }}>
            {[
              { label: t("chat.thread.meta.durationMs"), value: formatMetricValue(meta.durationMs, { unit: " ms" }), bar: meta.durationMs },
              { label: t("chat.thread.meta.totalTokens"), value: formatMetricValue(meta.totalTokens), bar: meta.totalTokens },
              { label: t("chat.thread.meta.tokensPerSecond"), value: formatMetricValue(meta.tokensPerSecond, { digits: 1 }), bar: meta.tokensPerSecond },
              { label: t("chat.thread.meta.costUsd"), value: formatMetricValue(meta.costUsd, { digits: 5 }), bar: meta.costUsd },
            ].map((row) => (
              <Box key={row.label} sx={{ p: 1, border: `1px solid ${tk.border.default}`, borderRadius: "6px", backgroundColor: tk.control.outlinedBg }}>
                <Typography sx={{ fontSize: "0.69rem", color: tk.text.secondary }}>{row.label}</Typography>
                <Typography sx={{ fontSize: "0.86rem", color: tk.text.primary, fontWeight: 600 }}>{row.value}</Typography>
                <Box sx={{ mt: 0.6, height: 4, borderRadius: 6, backgroundColor: tk.border.default, overflow: "hidden" }}>
                  <Box
                    sx={{
                      width: `${Math.min(100, Math.max(0, (((row.bar ?? 0) / maxMetaBar) * 100))) || 0}%`,
                      height: "100%",
                      backgroundColor: "rgba(99,102,241,0.65)",
                    }}
                  />
                </Box>
              </Box>
            ))}
          </Box>
          <Box sx={{ mt: 1, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0.5 }}>
            <Typography sx={{ fontSize: "0.76rem", color: tk.text.secondary }}>
              {t("chat.thread.meta.promptTokens")}: {formatMetricValue(meta.promptTokens)}
            </Typography>
            <Typography sx={{ fontSize: "0.76rem", color: tk.text.secondary }}>
              {t("chat.thread.meta.completionTokens")}: {formatMetricValue(meta.completionTokens)}
            </Typography>
            <Typography sx={{ fontSize: "0.76rem", color: tk.text.secondary }}>
              {t("chat.thread.meta.events")}: {formatMetricValue(meta.eventsCount)}
            </Typography>
            <Typography sx={{ fontSize: "0.76rem", color: tk.text.secondary }}>
              {t("chat.thread.meta.citations")}: {formatMetricValue(meta.citationCount)}
            </Typography>
          </Box>
          <Typography sx={{ mt: 0.8, fontSize: "0.76rem", color: tk.text.secondary }}>
            {t("chat.thread.meta.answerClass")}: {meta.answerClass || "—"}
          </Typography>
        </DialogContent>
      </Dialog>

      {showJump ? (
        <IconButton
          type="button"
          size="small"
          onClick={() => {
            stickToBottomRef.current = true;
            setStickToBottom(true);
            scrollContainerToBottom("smooth");
          }}
          aria-label={t("chat.thread.jumpBottomAria")}
          title={t("chat.thread.jumpBottomAria")}
          sx={{
            position: "absolute",
            right: 4,
            bottom: 8,
            zIndex: 2,
            border: `1px solid ${tk.border.strong}`,
            backgroundColor: tk.surface.panel,
            color: tk.text.secondary,
            "&:hover": { backgroundColor: tk.accent.softBg },
          }}
        >
          <KeyboardArrowDownRoundedIcon sx={{ fontSize: "1.15rem" }} />
        </IconButton>
      ) : null}

      <Box ref={endRef} sx={{ height: "1px", flexShrink: 0, width: "100%" }} />
    </Box>
  );
}
