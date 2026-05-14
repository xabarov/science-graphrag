import React, { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorSmallButton } from "../../../../common/index.js";
import { typedBlockOuterSx } from "../../../../../theme/chatTypedBlockSx.js";
import { TYPED_BLOCK_MATCH_CAP_DETAILED, TYPED_BLOCK_MATCH_PREVIEW_SIMPLE } from "./typedBlockConstants.js";

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   inventory: Record<string, unknown> | null | undefined,
 *   chatDetailLevel?: "simple" | "detailed",
 *   citationCount?: number,
 *   hasWeakEvidence?: boolean,
 * }}
 */
export function InventoryBlock({
  t,
  inventory,
  chatDetailLevel = "simple",
  citationCount = 0,
  hasWeakEvidence = false,
}) {
  const tk = useTheme().appTokens;
  const outer = useMemo(() => typedBlockOuterSx(tk), [tk]);
  const [matchesExpanded, setMatchesExpanded] = useState(false);

  if (!inventory || typeof inventory !== "object") return null;
  const papers = Array.isArray(inventory.papers) ? inventory.papers : null;
  const wc = inventory.work_count;
  const matches = Array.isArray(inventory.paper_matches) ? inventory.paper_matches : null;

  if (typeof wc === "number" && !papers && !matches) {
    return (
      <Box sx={outer}>
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, mb: 0.5 }}>{t("chat.typed.inventoryTitle")}</Typography>
        <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary }}>{t("chat.typed.workCount", { count: String(wc) })}</Typography>
      </Box>
    );
  }

  if (papers && papers.length > 0) {
    return (
      <Box sx={outer}>
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, mb: 0.75 }}>{t("chat.typed.papersTitle")}</Typography>
        <Box component="ul" sx={{ m: 0, pl: 2, pr: 0, py: 0 }}>
          {papers.slice(0, 40).map((p, i) => {
            const row = p && typeof p === "object" ? p : {};
            const title = String(row.title || row.work_id || "—").slice(0, 200);
            const wid = row.work_id != null ? String(row.work_id) : "";
            return (
              <Box component="li" key={wid || i} sx={{ mb: 0.5, fontSize: "0.8125rem", color: tk.text.primary }}>
                {title}
                {wid && chatDetailLevel === "detailed" ? (
                  <Typography component="span" sx={{ display: "block", fontSize: "0.7rem", color: tk.text.faint }}>
                    {wid}
                  </Typography>
                ) : null}
              </Box>
            );
          })}
        </Box>
      </Box>
    );
  }

  if (matches && matches.length > 0) {
    if (chatDetailLevel === "simple" && citationCount > 0 && !hasWeakEvidence) {
      return null;
    }
    const cap =
      chatDetailLevel === "detailed"
        ? TYPED_BLOCK_MATCH_CAP_DETAILED
        : matchesExpanded
          ? TYPED_BLOCK_MATCH_CAP_DETAILED
          : TYPED_BLOCK_MATCH_PREVIEW_SIMPLE;
    const slice = matches.slice(0, cap);
    const rest = Math.max(0, matches.length - TYPED_BLOCK_MATCH_PREVIEW_SIMPLE);
    const showToggle =
      chatDetailLevel === "simple" &&
      matches.length > TYPED_BLOCK_MATCH_PREVIEW_SIMPLE &&
      !matchesExpanded &&
      rest > 0;

    return (
      <Box sx={outer}>
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, mb: 0.75 }}>{t("chat.typed.matchesTitle")}</Typography>
        {slice.map((m, i) => (
          <Typography key={i} sx={{ fontSize: "0.75rem", mb: 0.35, color: tk.text.secondary }}>
            {typeof m === "string" ? m : String(m?.title || m?.work_id || JSON.stringify(m)).slice(0, 200)}
          </Typography>
        ))}
        {showToggle ? (
          <CursorSmallButton type="button" sx={{ mt: 0.5 }} onClick={() => setMatchesExpanded(true)}>
            {t("chat.typed.matchesShowMore", { n: String(rest) })}
          </CursorSmallButton>
        ) : null}
        {chatDetailLevel === "simple" && matchesExpanded && matches.length > TYPED_BLOCK_MATCH_PREVIEW_SIMPLE ? (
          <CursorSmallButton type="button" sx={{ mt: 0.5 }} onClick={() => setMatchesExpanded(false)}>
            {t("chat.typed.matchesShowLess")}
          </CursorSmallButton>
        ) : null}
      </Box>
    );
  }

  return (
    <Box sx={outer}>
      <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, mb: 0.5 }}>{t("chat.typed.inventoryTitle")}</Typography>
      <Typography
        component="pre"
        sx={{ fontSize: "0.7rem", m: 0, whiteSpace: "pre-wrap", wordBreak: "break-word", color: tk.text.secondary }}
      >
        {JSON.stringify(inventory, null, 2).slice(0, 4000)}
        {JSON.stringify(inventory, null, 2).length > 4000 ? "…" : ""}
      </Typography>
    </Box>
  );
}
