import React, { useCallback, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorSmallButton } from "../../common/index.js";
import { pickCitationBodyText } from "./citationBodyText.js";

const PREVIEW_CHARS = 280;
const EXPANDED_MAX_HEIGHT = "min(52vh, 420px)";

/**
 * Readable source passage for one citation: preview, expand/collapse, copy.
 *
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   citation: Record<string, unknown>,
 * }} props
 */
export function CitationBodyExpandable({ t, citation }) {
  const tk = useTheme().appTokens;
  const fullText = useMemo(() => pickCitationBodyText(citation).trim(), [citation]);
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const needsToggle = fullText.length > PREVIEW_CHARS;
  const truncated = useMemo(
    () => (needsToggle ? `${fullText.slice(0, PREVIEW_CHARS)}…` : fullText),
    [fullText, needsToggle],
  );

  const passageSx = {
    fontSize: "0.8125rem",
    lineHeight: 1.65,
    color: tk.text.primary,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  };

  const scrollBoxSx = {
    maxHeight: EXPANDED_MAX_HEIGHT,
    overflowY: "auto",
    pr: 0.5,
    scrollbarWidth: "thin",
    "&::-webkit-scrollbar": { width: 8, height: 8 },
    "&::-webkit-scrollbar-track": { background: "#0a0a0a", borderRadius: "4px" },
    "&::-webkit-scrollbar-thumb": {
      background: "#2a2a2a",
      borderRadius: "4px",
      "&:hover": { background: "#3a3a3a" },
    },
  };

  const onCopy = useCallback(async () => {
    if (!fullText) return;
    try {
      await navigator.clipboard.writeText(fullText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }, [fullText]);

  if (!fullText) {
    return (
      <Typography
        sx={{
          mt: 0.75,
          fontSize: "0.75rem",
          color: tk.text.faint,
          fontStyle: "italic",
          lineHeight: 1.5,
        }}
      >
        {t("askPanel.citation.noSnippet")}
      </Typography>
    );
  }

  return (
    <Box sx={{ mt: 0.75 }}>
      <Box
        sx={{
          pl: 1.25,
          pr: 0.5,
          py: 0.85,
          borderRadius: "6px",
          border: `1px solid ${tk.border.default}`,
          borderLeft: `3px solid rgba(129, 140, 248, 0.55)`,
          backgroundColor: tk.surface.panelAlt,
        }}
      >
        {!needsToggle ? (
          <Typography component="div" sx={passageSx}>
            {fullText}
          </Typography>
        ) : (
          <>
            <Collapse in={!expanded} timeout="auto" collapsedSize={0} unmountOnExit>
              <Typography component="div" sx={passageSx}>
                {truncated}
              </Typography>
            </Collapse>
            <Collapse in={expanded} timeout="auto" collapsedSize={0} unmountOnExit>
              <Box sx={scrollBoxSx}>
                <Typography component="div" sx={passageSx}>
                  {fullText}
                </Typography>
              </Box>
            </Collapse>
          </>
        )}
      </Box>

      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.75, mt: 0.65 }}>
        {needsToggle ? (
          <CursorSmallButton type="button" onClick={() => setExpanded((v) => !v)}>
            {expanded ? t("askPanel.citation.expandHide") : t("askPanel.citation.expandShow")}
          </CursorSmallButton>
        ) : null}
        <CursorSmallButton type="button" onClick={onCopy}>
          {copied ? t("askPanel.citation.copied") : t("askPanel.citation.copy")}
        </CursorSmallButton>
      </Box>
    </Box>
  );
}
