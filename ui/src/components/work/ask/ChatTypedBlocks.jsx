import React, { useCallback, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorSmallButton } from "../../common/index.js";
import { typedBlockOuterSx } from "../../../theme/chatTypedBlockSx.js";

/**
 * @param {{ t: (key: string, vars?: Record<string, string>) => string, inventory: Record<string, unknown> | null | undefined }}
 */
export function InventoryBlock({ t, inventory }) {
  const tk = useTheme().appTokens;
  const outer = useMemo(() => typedBlockOuterSx(tk), [tk]);

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
                {wid ? (
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
    return (
      <Box sx={outer}>
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, mb: 0.75 }}>{t("chat.typed.matchesTitle")}</Typography>
        {matches.slice(0, 20).map((m, i) => (
          <Typography key={i} sx={{ fontSize: "0.75rem", mb: 0.35, color: tk.text.secondary }}>
            {typeof m === "string" ? m : String(m?.title || m?.work_id || JSON.stringify(m)).slice(0, 200)}
          </Typography>
        ))}
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

/**
 * @param {{ t: (key: string, vars?: Record<string, string>) => string, candidates: Array<Record<string, unknown>> | null | undefined }}
 */
export function QuoteCandidatesBlock({ t, candidates }) {
  const tk = useTheme().appTokens;
  const outer = useMemo(() => typedBlockOuterSx(tk), [tk]);

  if (!Array.isArray(candidates) || candidates.length === 0) return null;
  const rows = candidates.slice(0, 12);
  return (
    <Box sx={outer}>
      <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, mb: 0.75 }}>{t("chat.typed.quotesTitle")}</Typography>
      {rows.map((c, i) => {
        const text = String(c?.quote_text || c?.text || c?.snippet || "").slice(0, 800);
        const sec = c?.section != null ? String(c.section) : "";
        const wid = c?.work_id != null ? String(c.work_id) : "";
        const isLast = i === rows.length - 1;
        return (
          <Box
            key={i}
            sx={{
              mb: isLast ? 0 : 1,
              pb: isLast ? 0 : 1,
              borderBottom: isLast ? "none" : `1px solid ${tk.border.default}`,
            }}
          >
            <Typography sx={{ fontSize: "0.75rem", color: tk.text.faint, mb: 0.5 }}>
              {wid}
              {sec ? ` · ${sec}` : ""}
            </Typography>
            <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, fontStyle: "italic", whiteSpace: "pre-wrap" }}>
              “{text}”
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
}

/**
 * @param {{ t: (key: string, vars?: Record<string, string>) => string, bibliography: Record<string, unknown> | null | undefined }}
 */
export function BibliographyBlock({ t, bibliography }) {
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
      {filtered.length > 0 ? (
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
 * @param {{ t: (key: string, vars?: Record<string, string>) => string, relationTrace: Record<string, unknown> | null | undefined }}
 */
export function RelationTraceBlock({ t, relationTrace }) {
  const tk = useTheme().appTokens;
  const outer = useMemo(() => typedBlockOuterSx(tk), [tk]);

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
