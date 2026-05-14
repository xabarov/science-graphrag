import React, { useCallback, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorSmallButton } from "../../../common/index.js";
import { pickCitationBodyText } from "./citationBodyText.js";

const PREVIEW_CHARS = 280;
const EXPANDED_MAX_HEIGHT = "min(52vh, 420px)";

/**
 * Readable source passage for one citation: preview, expand/collapse, copy.
 *
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   citation: Record<string, unknown>,
 *   defaultExpanded?: boolean,
 *   suppressMissingPlaceholder?: boolean,
 *   trailingActions?: import("react").ReactNode,
 * }} props
 */
export function CitationBodyExpandable({
  t,
  citation,
  defaultExpanded = true,
  suppressMissingPlaceholder = false,
  trailingActions = null,
}) {
  const tk = useTheme().appTokens;
  const fullText = useMemo(() => pickCitationBodyText(citation).trim(), [citation]);
  const needsToggle = fullText.length > PREVIEW_CHARS;
  const [expanded, setExpanded] = useState(() => (needsToggle ? defaultExpanded : true));
  const [copied, setCopied] = useState(false);

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
    if (suppressMissingPlaceholder) {
      return trailingActions ? (
        <Box
          sx={{
            mt: 0.75,
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "flex-end",
            gap: 0.35,
          }}
          data-testid="citation-trailing-actions"
        >
          {trailingActions}
        </Box>
      ) : null;
    }
    return (
      <Box sx={{ mt: 0.75 }}>
        <Box
          sx={{
            py: 1,
            px: 1.1,
            borderRadius: "8px",
            border: `1px dashed ${tk.border.default}`,
            backgroundColor: "rgba(255, 255, 255, 0.02)",
          }}
        >
          <Typography
            sx={{
              fontSize: "0.75rem",
              color: tk.text.muted,
              lineHeight: 1.55,
            }}
          >
            {t("askPanel.citation.noSnippet")}
          </Typography>
        </Box>
        {trailingActions ? (
          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              justifyContent: "flex-end",
              gap: 0.35,
              mt: 0.65,
            }}
            data-testid="citation-trailing-actions"
          >
            {trailingActions}
          </Box>
        ) : null}
      </Box>
    );
  }

  return (
    <Box sx={{ mt: 0.75 }}>
      <Box
        sx={{
          pl: 1.35,
          pr: 0.85,
          py: 1,
          borderRadius: "8px",
          border: `1px solid ${tk.border.default}`,
          borderLeft: `4px solid rgba(129, 140, 248, 0.65)`,
          backgroundColor: tk.surface.panelAlt,
          boxShadow: "inset 0 1px 0 rgba(255,255,255,0.04)",
        }}
      >
        <Typography
          component="div"
          sx={{
            fontSize: "0.65rem",
            fontWeight: 600,
            letterSpacing: "0.04em",
            textTransform: "uppercase",
            color: tk.text.faint,
            mb: 0.65,
          }}
        >
          {t("askPanel.citation.passageLabel")}
        </Typography>
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

      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 0.75,
          mt: 0.65,
          rowGap: 0.5,
        }}
      >
        <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.75 }}>
          {needsToggle ? (
            <CursorSmallButton type="button" onClick={() => setExpanded((v) => !v)}>
              {expanded ? t("askPanel.citation.expandHide") : t("askPanel.citation.expandShow")}
            </CursorSmallButton>
          ) : null}
          <CursorSmallButton type="button" onClick={onCopy}>
            {copied ? t("askPanel.citation.copied") : t("askPanel.citation.copy")}
          </CursorSmallButton>
        </Box>
        {trailingActions ? (
          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: 0.35,
              flexBasis: { xs: "100%", sm: "auto" },
              width: { xs: "100%", sm: "auto" },
              justifyContent: { xs: "flex-end", sm: "flex-start" },
              pl: { xs: 0, sm: 1 },
              ml: { xs: 0, sm: "auto" },
              mt: { xs: 0.25, sm: 0 },
              borderLeft: { xs: "none", sm: `1px solid ${tk.border.default}` },
            }}
            data-testid="citation-trailing-actions"
          >
            {trailingActions}
          </Box>
        ) : null}
      </Box>
    </Box>
  );
}
