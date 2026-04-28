import React, { useId, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import { CursorSmallButton } from "../common/index.js";
import { ShimmerLabel } from "./ShimmerLabel.jsx";
import { buildLiveStatusPresentation } from "./agentRunViewModel.js";

/**
 * Compact live card for an in-flight (or just-finished) agent turn: one headline, optional
 * tool activity chips, safe explanations, and optional recent-line history.
 *
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   streamEvents: unknown[],
 *   isActive: boolean,
 *   embedded?: boolean,
 * }} props
 */
export function AgentLiveStatus({ t, streamEvents = [], isActive, embedded = false }) {
  const tk = useTheme().appTokens;
  const presentation = useMemo(
    () => buildLiveStatusPresentation(t, streamEvents, isActive),
    [t, streamEvents, isActive],
  );
  const { headline, activityChips, explanations, recentLines, showRecentToggle, showExplainToggle } = presentation;

  const [recentOpen, setRecentOpen] = useState(false);
  const [explainOpen, setExplainOpen] = useState(false);
  const recentPanelId = useId();
  const explainPanelId = useId();

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
      <Typography variant="caption" sx={{ color: tk.text.faint, fontSize: "0.68rem", display: "block", mb: embedded ? 0.35 : 0.65 }}>
        {t("chat.run.liveRunCardTitle")}
      </Typography>

      <Box aria-live="polite" aria-atomic="false">
        {isActive && !headline ? (
          <ShimmerLabel component="span" sx={{ fontSize: "0.8125rem", fontWeight: 600 }}>
            {t("chat.stream.thinking")}
          </ShimmerLabel>
        ) : (
          <Typography
            sx={{
              fontSize: "0.8125rem",
              fontWeight: 600,
              color: tk.text.primary,
              lineHeight: 1.45,
              wordBreak: "break-word",
              transition: "opacity 0.18s ease",
            }}
          >
            {headline || t("chat.stream.thinking")}
          </Typography>
        )}
      </Box>

      {activityChips.length > 0 ? (
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 0.75, alignItems: "center" }}>
          {activityChips.map(({ tool, label }) => (
            <Chip
              key={tool}
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
