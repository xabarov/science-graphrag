import React, { useId, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorSmallButton } from "../../../../common/index.js";
import { typedBlockOuterSx } from "../../../../../theme/chatTypedBlockSx.js";
import { pickQuoteWorkTitle } from "./quoteCandidatesHelpers.js";

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   candidates: Array<Record<string, unknown>> | null | undefined,
 *   chatDetailLevel?: "simple" | "detailed",
 * }}
 */
export function QuoteCandidatesBlock({ t, candidates, chatDetailLevel = "simple" }) {
  const tk = useTheme().appTokens;
  const outer = useMemo(() => typedBlockOuterSx(tk), [tk]);
  const quotePanelId = useId();
  const quoteToggleId = `${quotePanelId}-toggle`;
  const quoteRegionId = `${quotePanelId}-region`;
  const [simpleOpen, setSimpleOpen] = useState(false);
  const expanded = chatDetailLevel === "detailed" || simpleOpen;

  if (!Array.isArray(candidates) || candidates.length === 0) return null;
  const rows = candidates.slice(0, 12);
  const count = rows.length;

  const rowsEl = rows.map((c, i) => {
    const text = String(c?.quote_text || c?.text || c?.snippet || "").slice(0, 800);
    const sec = c?.section != null ? String(c.section) : "";
    const wid = c?.work_id != null ? String(c.work_id) : "";
    const workTitle = pickQuoteWorkTitle(c);
    const isLast = i === rows.length - 1;
    const metaBits = [];
    if (wid && workTitle) metaBits.push(wid);
    if (sec) metaBits.push(sec);
    const metaLine = metaBits.join(" · ");
    return (
      <Box
        key={i}
        sx={{
          mb: isLast ? 0 : 1,
          pb: isLast ? 0 : 1,
          borderBottom: isLast ? "none" : `1px solid ${tk.border.default}`,
        }}
      >
        {workTitle ? (
          <>
            <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, mb: 0.35 }}>{workTitle}</Typography>
            {metaLine ? (
              <Typography sx={{ fontSize: "0.68rem", color: tk.text.faint, mb: 0.5 }}>{metaLine}</Typography>
            ) : null}
          </>
        ) : (
          <Typography sx={{ fontSize: "0.75rem", color: tk.text.faint, mb: 0.5 }}>
            {wid}
            {sec ? ` · ${sec}` : ""}
          </Typography>
        )}
        <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, fontStyle: "italic", whiteSpace: "pre-wrap" }}>
          “{text}”
        </Typography>
      </Box>
    );
  });

  const inner = (
    <>
      <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, mb: 0.75 }}>{t("chat.typed.quotesTitle")}</Typography>
      {rowsEl}
    </>
  );

  if (chatDetailLevel === "detailed") {
    return <Box sx={outer}>{inner}</Box>;
  }

  return (
    <Box sx={outer}>
      <CursorSmallButton
        type="button"
        onClick={() => setSimpleOpen((v) => !v)}
        aria-expanded={expanded}
        aria-controls={quoteRegionId}
        id={quoteToggleId}
        data-testid="quote-candidates-toggle"
      >
        {expanded ? t("chat.typed.quoteCandidatesCollapse") : t("chat.typed.quoteCandidatesExpand", { n: String(count) })}
      </CursorSmallButton>
      <Collapse in={expanded} timeout="auto" unmountOnExit>
        <Box id={quoteRegionId} role="region" aria-labelledby={quoteToggleId} sx={{ mt: 1 }}>
          {inner}
        </Box>
      </Collapse>
    </Box>
  );
}
