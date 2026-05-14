import React, { useCallback, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorSmallButton } from "../../../../common/index.js";
import { typedBlockOuterSx } from "../../../../../theme/chatTypedBlockSx.js";

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
