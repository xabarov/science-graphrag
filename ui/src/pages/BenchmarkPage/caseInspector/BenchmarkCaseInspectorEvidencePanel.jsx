import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../../../components/common/index.js";

/**
 * Right column: evidence links and last-run shortcut.
 *
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   evidenceLinks: unknown[],
 *   onOpenRun: (runId: string) => void,
 *   t: (key: string, vars?: Record<string, string | number>) => string,
 * }} props
 */
export default function BenchmarkCaseInspectorEvidencePanel({ tk, evidenceLinks, onOpenRun, t }) {
  return (
    <Box
      sx={{
        border: `1px solid ${tk.border.default}`,
        borderRadius: 1.5,
        backgroundColor: tk.surface.panel,
        p: 1.5,
      }}
    >
      <Typography sx={{ fontWeight: 600, mb: 1, fontSize: "0.8125rem" }}>{t("benchmark.inspector.evidence.title")}</Typography>
      {evidenceLinks.length === 0 ? (
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted }}>{t("benchmark.inspector.evidence.empty")}</Typography>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          {evidenceLinks.map((link, linkIdx) => {
            if (!link || typeof link !== "object") return null;
            const L = /** @type {Record<string, unknown>} */ (link);
            const id = String(L.id || "");
            if (id === "last_completed_run" && L.run_id) {
              return (
                <Box key={`${id}-${String(L.run_id)}`} sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
                  <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary }}>{t("benchmark.inspector.evidence.lastRun")}</Typography>
                  <CursorSmallButton onClick={() => onOpenRun(String(L.run_id))}>
                    {t("benchmark.inspector.evidence.openRun", { id: String(L.run_id).slice(0, 8) })}
                  </CursorSmallButton>
                </Box>
              );
            }
            return (
              <Box key={id ? `${id}-${linkIdx}` : `ev-${linkIdx}`}>
                <Typography sx={{ fontSize: "0.7rem", color: tk.text.muted }}>{String(L.label || L.id)}</Typography>
                <Typography sx={{ fontSize: "0.75rem", wordBreak: "break-all", fontFamily: "monospace" }}>
                  {L.path_relative_to_repo ? String(L.path_relative_to_repo) : "—"}
                </Typography>
              </Box>
            );
          })}
        </Box>
      )}
    </Box>
  );
}
