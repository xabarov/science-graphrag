import React, { useId, useState } from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import { CursorSmallButton } from "../common/index.js";
import { ShimmerLabel } from "./ShimmerLabel.jsx";
import {
  collectFormattedStreamLines,
  formatStreamEventOneLine,
  pickLastMeaningfulStreamEvent,
} from "./agentRunViewModel.js";

/**
 * Compact live strip for an in-flight agent turn.
 *
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   streamEvents: unknown[],
 *   isActive: boolean,
 * }} props
 */
export function AgentLiveStatus({ t, streamEvents = [], isActive }) {
  const tk = useTheme().appTokens;
  const list = Array.isArray(streamEvents) ? streamEvents : [];
  const last = pickLastMeaningfulStreamEvent(list);
  const line = last ? formatStreamEventOneLine(t, last) : "";
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const recentLines = collectFormattedStreamLines(t, list, 24);
  const rawCount = list.filter((e) => e && typeof e === "object").length;
  const showDetailsToggle = rawCount >= 2;

  if (!isActive && !line) return null;

  return (
    <Box
      sx={{
        mb: 1.25,
        pb: 1,
        borderBottom: `1px solid ${tk.border.default}`,
      }}
    >
      <Typography variant="caption" sx={{ color: tk.text.faint, fontSize: "0.68rem", display: "block", mb: 0.5 }}>
        {t("chat.run.liveStripTitle")}
      </Typography>
      <Box aria-live="polite" aria-atomic="false">
        {isActive && !line ? (
          <ShimmerLabel component="span" sx={{ fontSize: "0.78rem", fontWeight: 500 }}>
            {t("chat.stream.thinking")}
          </ShimmerLabel>
        ) : (
          <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, lineHeight: 1.45, wordBreak: "break-word" }}>
            {line || t("chat.stream.thinking")}
          </Typography>
        )}
      </Box>
      {showDetailsToggle ? (
        <Box sx={{ mt: 0.75 }}>
          <CursorSmallButton
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-controls={panelId}
            aria-label={open ? t("chat.run.liveStatusCollapseAria") : t("chat.run.liveStatusExpandAria")}
            sx={{ minHeight: 26, py: 0.25 }}
          >
            {open ? t("chat.run.liveStatusHideRecent") : t("chat.run.liveStatusShowRecent")}
          </CursorSmallButton>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box
              id={panelId}
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
