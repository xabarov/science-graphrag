import React, { useCallback, useId, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorSmallButton } from "../../common/index.js";
import { typedBlockOuterSx } from "../../../theme/chatTypedBlockSx.js";

const MATCH_PREVIEW_SIMPLE = 3;
const MATCH_CAP_DETAILED = 20;

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
    const cap = chatDetailLevel === "detailed" ? MATCH_CAP_DETAILED : matchesExpanded ? MATCH_CAP_DETAILED : MATCH_PREVIEW_SIMPLE;
    const slice = matches.slice(0, cap);
    const rest = Math.max(0, matches.length - MATCH_PREVIEW_SIMPLE);
    const showToggle =
      chatDetailLevel === "simple" && matches.length > MATCH_PREVIEW_SIMPLE && !matchesExpanded && rest > 0;

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
        {chatDetailLevel === "simple" && matchesExpanded && matches.length > MATCH_PREVIEW_SIMPLE ? (
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

function pickQuoteWorkTitle(c) {
  if (!c || typeof c !== "object") return "";
  const raw = c.title ?? c.work_title ?? c.paper_title;
  return raw != null ? String(raw).trim() : "";
}

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

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   bibliography: Record<string, unknown> | null | undefined,
 *   chatDetailLevel?: "simple" | "detailed",
 * }}
 */
export function BibliographyBlock({ t, bibliography, chatDetailLevel = "simple" }) {
  const tk = useTheme().appTokens;
  const outer = useMemo(() => typedBlockOuterSx(tk), [tk]);

  const entries =
    bibliography && typeof bibliography === "object" && Array.isArray(bibliography.entries)
      ? bibliography.entries
      : [];
  const text = entries.map((e) => String(e)).join("\n");
  const [copied, setCopied] = useState(false);
  const onCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }, [text]);

  if (!bibliography || typeof bibliography !== "object" || entries.length === 0) return null;

  const filtered = Array.isArray(bibliography.filtered_work_ids) ? bibliography.filtered_work_ids : [];
  const bibWarnings = Array.isArray(bibliography.warnings) ? bibliography.warnings : [];

  return (
    <Box sx={outer}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1, mb: 0.75 }}>
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted }}>{t("chat.typed.bibTitle")}</Typography>
        <CursorSmallButton type="button" onClick={onCopy}>
          {copied ? t("chat.typed.copied") : t("chat.typed.copyBib")}
        </CursorSmallButton>
      </Box>
      {bibWarnings.length > 0 ? (
        <Typography sx={{ fontSize: "0.7rem", color: "warning.main", mb: 0.75 }}>
          {bibWarnings.map((w) => String(w)).join(" · ")}
        </Typography>
      ) : null}
      {chatDetailLevel === "detailed" && filtered.length > 0 ? (
        <Typography sx={{ fontSize: "0.68rem", color: tk.text.faint, mb: 0.75, fontFamily: "monospace" }}>
          {t("chat.typed.filteredWorkIds")}:{" "}
          {(() => {
            const joined = filtered.map((id) => String(id)).join(", ");
            return joined.length > 800 ? `${joined.slice(0, 800)}…` : joined;
          })()}
        </Typography>
      ) : null}
      <Box component="ol" sx={{ m: 0, pl: 2, color: tk.text.primary, fontSize: "0.8125rem" }}>
        {entries.map((e, i) => (
          <Box component="li" key={i} sx={{ mb: 0.5 }}>
            {String(e)}
          </Box>
        ))}
      </Box>
    </Box>
  );
}

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   relationTrace: Record<string, unknown> | null | undefined,
 *   chatDetailLevel?: "simple" | "detailed",
 * }}
 */
export function RelationTraceBlock({ t, relationTrace, chatDetailLevel = "simple" }) {
  const tk = useTheme().appTokens;
  const outer = useMemo(() => typedBlockOuterSx(tk), [tk]);

  if (chatDetailLevel !== "detailed") return null;
  if (!relationTrace || typeof relationTrace !== "object") return null;
  const keys = Object.keys(relationTrace);
  if (keys.length === 0) return null;
  const raw = JSON.stringify(relationTrace, null, 2);
  return (
    <Box sx={outer}>
      <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, mb: 0.75 }}>{t("chat.typed.relationTraceTitle")}</Typography>
      <Typography
        component="pre"
        sx={{ fontSize: "0.7rem", m: 0, whiteSpace: "pre-wrap", wordBreak: "break-word", color: tk.text.secondary }}
      >
        {raw.slice(0, 6000)}
        {raw.length > 6000 ? "…" : ""}
      </Typography>
    </Box>
  );
}

/**
 * @param {{ t: (key: string, vars?: Record<string, string>) => string, suggestions: Array<Record<string, unknown>> | null | undefined }}
 */
export function IdeaSuggestionsBlock({ t, suggestions }) {
  const tk = useTheme().appTokens;
  const outer = useMemo(() => typedBlockOuterSx(tk), [tk]);

  if (!Array.isArray(suggestions) || suggestions.length === 0) return null;
  return (
    <Box sx={outer}>
      <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, mb: 0.75 }}>{t("chat.typed.ideaSuggestionsTitle")}</Typography>
      {suggestions.slice(0, 12).map((row, i) => (
        <Typography key={i} sx={{ fontSize: "0.78rem", color: tk.text.secondary, mb: 0.5, whiteSpace: "pre-wrap" }}>
          {typeof row === "string" ? row.slice(0, 800) : JSON.stringify(row).slice(0, 800)}
        </Typography>
      ))}
    </Box>
  );
}
