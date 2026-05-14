import React, { useId, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import { useReducedMotionGate } from "../shared/useReducedMotionGate.js";
import { deriveAgentLiveStatusChrome } from "./agentLiveStatusChrome.js";
import { buildLiveStatusPresentation } from "./agentRunViewModel.js";
import { AgentLiveStatusActivityChips } from "./AgentLiveStatusActivityChips.jsx";
import { AgentLiveStatusDecisionSection } from "./AgentLiveStatusDecisionSection.jsx";
import { AgentLiveStatusHeadlineRegion } from "./AgentLiveStatusHeadlineRegion.jsx";
import { AgentLiveStatusStreamPanels } from "./AgentLiveStatusStreamPanels.jsx";
import { useAgentLiveStatusExplainAutoOpen } from "./useAgentLiveStatusExplainAutoOpen.js";

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
  const reducedMotion = useReducedMotionGate();
  const presentation = useMemo(
    () => buildLiveStatusPresentation(t, streamEvents, isActive),
    [t, streamEvents, isActive],
  );
  const {
    headline,
    decision,
    why,
    latestAgentNote,
    explanations,
    recentLines,
  } = presentation;

  const { isSimple, minimalEmbeddedChrome, activityChips, showRecentToggle, showExplainToggle } = useMemo(
    () => deriveAgentLiveStatusChrome(presentation, { chatDetailLevel, embedded }),
    [presentation, chatDetailLevel, embedded],
  );

  const decisionKey = `${decision}|${why}`;

  const [recentOpen, setRecentOpen] = useState(false);
  const [explainOpen, setExplainOpen] = useState(false);
  const recentPanelId = useId();
  const explainPanelId = useId();

  useAgentLiveStatusExplainAutoOpen({
    isSimple,
    isActive,
    showExplainToggle,
    streamEvents,
    setExplainOpen,
  });

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

      {!minimalEmbeddedChrome ? (
        <AgentLiveStatusDecisionSection
          t={t}
          tk={tk}
          reducedMotion={reducedMotion}
          decision={decision}
          why={why}
          latestAgentNote={latestAgentNote}
          decisionKey={decisionKey}
          isSimple={isSimple}
        />
      ) : null}

      <AgentLiveStatusHeadlineRegion
        t={t}
        tk={tk}
        reducedMotion={reducedMotion}
        isActive={isActive}
        headline={headline}
      />

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

      <AgentLiveStatusActivityChips activityChips={activityChips} tk={tk} reducedMotion={reducedMotion} />

      <AgentLiveStatusStreamPanels
        t={t}
        tk={tk}
        showExplainToggle={showExplainToggle}
        showRecentToggle={showRecentToggle}
        explainOpen={explainOpen}
        setExplainOpen={setExplainOpen}
        recentOpen={recentOpen}
        setRecentOpen={setRecentOpen}
        explainPanelId={explainPanelId}
        recentPanelId={recentPanelId}
        explanations={explanations}
        recentLines={recentLines}
      />
    </Box>
  );
}
