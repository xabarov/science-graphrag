import React from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import { CursorSmallButton } from "../../common/index.js";

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   showExplainToggle: boolean,
 *   showRecentToggle: boolean,
 *   explainOpen: boolean,
 *   setExplainOpen: import("react").Dispatch<import("react").SetStateAction<boolean>>,
 *   recentOpen: boolean,
 *   setRecentOpen: import("react").Dispatch<import("react").SetStateAction<boolean>>,
 *   explainPanelId: string,
 *   recentPanelId: string,
 *   explanations: string[],
 *   recentLines: string[],
 * }} props
 */
export function AgentLiveStatusStreamPanels({
  t,
  tk,
  showExplainToggle,
  showRecentToggle,
  explainOpen,
  setExplainOpen,
  recentOpen,
  setRecentOpen,
  explainPanelId,
  recentPanelId,
  explanations,
  recentLines,
}) {
  return (
    <>
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
    </>
  );
}
