import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import { keyframes } from "@mui/system";
import { useTheme } from "@mui/material/styles";
import { CursorSmallButton } from "../../common/index.js";
import { ShimmerLabel } from "../shared/ShimmerLabel.jsx";
import { useReducedMotionGate } from "../shared/useReducedMotionGate.js";
import { buildLiveStatusPresentation } from "./agentRunViewModel.js";

const decisionGlow = keyframes`
  0% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.0); }
  20% { box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.30); }
  100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.0); }
`;

const decisionFadeIn = keyframes`
  0% { opacity: 0; transform: translateY(2px); }
  100% { opacity: 1; transform: translateY(0); }
`;

const chipPop = keyframes`
  0% { transform: scale(0.96); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
`;

/**
 * Compact live card for an in-flight (or just-finished) agent turn: one headline, optional
 * tool activity chips, safe explanations, and optional recent-line history.
 *
 * In the `simple` detail level the recent-lines collapse and "How the agent is
 * working" reasoning panel are suppressed. When ``embedded`` (Ask/chat rail),
 * the progress caption, decision/why rows, and tool activity chips are omitted so
 * only the dynamic headline (and optional detailed panels / agent note) remain.
 *
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   streamEvents: unknown[],
 *   isActive: boolean,
 *   embedded?: boolean,
 *   chatDetailLevel?: "simple" | "detailed",
 * }} props
 */
export function AgentLiveStatus({
  t,
  streamEvents = [],
  isActive,
  embedded = false,
  chatDetailLevel = "simple",
}) {
  const tk = useTheme().appTokens;
  const presentation = useMemo(
    () => buildLiveStatusPresentation(t, streamEvents, isActive),
    [t, streamEvents, isActive],
  );
  const {
    headline,
    decision,
    why,
    latestAgentNote,
    activityChips: rawChips,
    explanations,
    recentLines,
    showRecentToggle: rawShowRecentToggle,
    showExplainToggle: rawShowExplainToggle,
  } = presentation;

  const isSimple = chatDetailLevel !== "detailed";
  const minimalEmbeddedChrome = Boolean(embedded);
  const activityChips =
    minimalEmbeddedChrome ? [] : isSimple ? rawChips.slice(0, 2) : rawChips;
  const showRecentToggle = !isSimple && rawShowRecentToggle;
  const showExplainToggle = !isSimple && rawShowExplainToggle;
  const reducedMotion = useReducedMotionGate();
  const decisionKey = `${decision}|${why}`;

  const [recentOpen, setRecentOpen] = useState(false);
  const [explainOpen, setExplainOpen] = useState(false);
  const recentPanelId = useId();
  const explainPanelId = useId();
  const autoExplainOpenedRef = useRef(false);

  useEffect(() => {
    if (!isActive) autoExplainOpenedRef.current = false;
  }, [isActive]);

  useEffect(() => {
    if (isSimple || !isActive || !showExplainToggle) return;
    if (autoExplainOpenedRef.current) return;
    const evList = Array.isArray(streamEvents) ? streamEvents : [];
    const hasIntent = evList.some(
      (e) => e && typeof e === "object" && String(e.type) === "intent_classified",
    );
    if (!hasIntent) return;
    autoExplainOpenedRef.current = true;
    queueMicrotask(() => {
      setExplainOpen(true);
    });
  }, [isSimple, isActive, showExplainToggle, streamEvents]);

  if (!isActive && !headline) return null;

  const outerSx = embedded
    ? {
        mb: 1,
        pb: 1,
        borderBottom: `1px solid ${tk.border.default}`,
        backgroundColor: "transparent",
      }
    : {
        mb: 1.25,
        p: 1,
        borderRadius: "6px",
        border: `1px solid ${tk.border.default}`,
        backgroundColor: tk.surface.panelAlt,
      };

  return (
    <Box sx={outerSx}>
      {!minimalEmbeddedChrome ? (
        <Typography
          variant="caption"
          sx={{
            color: tk.text.faint,
            fontSize: "0.68rem",
            display: "block",
            mb: embedded ? 0.35 : 0.65,
          }}
        >
          {t("chat.run.liveRunCardTitle")}
        </Typography>
      ) : null}

      {!minimalEmbeddedChrome && (decision || why || (!isSimple && latestAgentNote)) ? (
        <Box
          key={`${decisionKey}|${latestAgentNote}`}
          role="group"
          aria-label={t("chat.run.decision.label")}
          sx={{
            mb: 0.6,
            display: "flex",
            flexDirection: "column",
            gap: 0.15,
            borderRadius: "4px",
            ...(reducedMotion
              ? {}
              : {
                  animation: `${decisionFadeIn} 0.22s ease, ${decisionGlow} 0.6s ease`,
                }),
          }}
        >
          {decision ? (
            <Typography
              sx={{
                fontSize: "0.72rem",
                color: tk.text.secondary,
                lineHeight: 1.4,
                wordBreak: "break-word",
              }}
            >
              {t("chat.run.decision.row", { label: t("chat.run.decision.label"), value: decision })}
            </Typography>
          ) : null}
          {why ? (
            <Typography
              sx={{
                fontSize: "0.72rem",
                color: tk.text.muted,
                lineHeight: 1.4,
                wordBreak: "break-word",
              }}
            >
              {t("chat.run.decision.row", { label: t("chat.run.decision.why"), value: why })}
            </Typography>
          ) : null}
          {!isSimple && latestAgentNote ? (
            <Typography
              data-testid="agent-note-row"
              sx={{
                fontSize: "0.72rem",
                color: tk.text.muted,
                fontStyle: "italic",
                lineHeight: 1.4,
                wordBreak: "break-word",
              }}
            >
              {t("chat.run.decision.row", {
                label: t("chat.run.agentNote.label"),
                value: latestAgentNote,
              })}
            </Typography>
          ) : null}
        </Box>
      ) : null}

      <Box aria-live="polite" aria-atomic="false">
        {isActive && !headline ? (
          <ShimmerLabel component="span" intensity="subtle" sx={{ fontSize: "0.8125rem", fontWeight: 600 }}>
            {t("chat.stream.thinking")}
          </ShimmerLabel>
        ) : isActive && headline ? (
          <ShimmerLabel
            component="span"
            intensity="strong"
            sx={{
              fontSize: "0.8125rem",
              fontWeight: 600,
              lineHeight: 1.45,
              wordBreak: "break-word",
              maxWidth: "100%",
            }}
          >
            {headline}
          </ShimmerLabel>
        ) : (
          <Typography
            key={headline}
            sx={{
              fontSize: "0.8125rem",
              fontWeight: 600,
              color: tk.text.primary,
              lineHeight: 1.45,
              wordBreak: "break-word",
              transition: "opacity 0.18s ease",
              ...(reducedMotion ? {} : { animation: `${decisionFadeIn} 0.18s ease` }),
            }}
          >
            {headline || t("chat.stream.thinking")}
          </Typography>
        )}
      </Box>

      {minimalEmbeddedChrome && !isSimple && latestAgentNote ? (
        <Typography
          data-testid="agent-note-row"
          sx={{
            mt: 0.45,
            fontSize: "0.72rem",
            color: tk.text.muted,
            fontStyle: "italic",
            lineHeight: 1.4,
            wordBreak: "break-word",
          }}
        >
          {t("chat.run.decision.row", {
            label: t("chat.run.agentNote.label"),
            value: latestAgentNote,
          })}
        </Typography>
      ) : null}

      {activityChips.length > 0 ? (
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 0.75, alignItems: "center" }}>
          {activityChips.map(({ tool, label }, chipIdx) => (
            <Chip
              key={`${tool}-${chipIdx}`}
              size="small"
              label={label}
              sx={{
                height: 22,
                fontSize: "0.68rem",
                color: tk.text.secondary,
                backgroundColor: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.1)",
                maxWidth: "100%",
                transition: "border-color 0.15s ease, background-color 0.15s ease",
                ...(reducedMotion ? {} : { animation: `${chipPop} 0.18s ease` }),
              }}
            />
          ))}
        </Box>
      ) : null}

      {showExplainToggle ? (
        <Box sx={{ mt: 0.85 }}>
          <CursorSmallButton
            type="button"
            onClick={() => setExplainOpen((v) => !v)}
            aria-expanded={explainOpen}
            aria-controls={explainPanelId}
            aria-label={explainOpen ? t("chat.run.liveExplainCollapseAria") : t("chat.run.liveExplainExpandAria")}
            sx={{ minHeight: 26, py: 0.25 }}
          >
            {explainOpen ? t("chat.run.liveExplainHide") : t("chat.run.liveExplainShow")}
          </CursorSmallButton>
          <Collapse in={explainOpen} timeout="auto" unmountOnExit>
            <Box
              id={explainPanelId}
              role="region"
              aria-label={t("chat.run.liveExplainRegionTitle")}
              sx={{ mt: 0.5, pl: 0.25, pt: 0.25 }}
            >
              {explanations.map((text, idx) => (
                <Typography
                  key={`explain-${idx}`}
                  sx={{ fontSize: "0.68rem", color: tk.text.muted, lineHeight: 1.4, mb: 0.35 }}
                >
                  {text}
                </Typography>
              ))}
            </Box>
          </Collapse>
        </Box>
      ) : null}

      {showRecentToggle ? (
        <Box sx={{ mt: showExplainToggle ? 0.5 : 0.85 }}>
          <CursorSmallButton
            type="button"
            onClick={() => setRecentOpen((v) => !v)}
            aria-expanded={recentOpen}
            aria-controls={recentPanelId}
            aria-label={recentOpen ? t("chat.run.liveStatusCollapseAria") : t("chat.run.liveStatusExpandAria")}
            sx={{ minHeight: 26, py: 0.25 }}
          >
            {recentOpen ? t("chat.run.liveStatusHideRecent") : t("chat.run.liveStatusShowRecent")}
          </CursorSmallButton>
          <Collapse in={recentOpen} timeout="auto" unmountOnExit>
            <Box
              id={recentPanelId}
              role="region"
              aria-label={t("chat.run.liveStatusRecentTitle")}
              sx={{ mt: 0.5, pl: 0.25, pt: 0.25 }}
            >
              {recentLines.map((text, idx) => (
                <Typography
                  key={`live-line-${idx}`}
                  sx={{ fontSize: "0.68rem", color: tk.text.muted, lineHeight: 1.35, mb: 0.15 }}
                >
                  {text}
                </Typography>
              ))}
            </Box>
          </Collapse>
        </Box>
      ) : null}
    </Box>
  );
}
