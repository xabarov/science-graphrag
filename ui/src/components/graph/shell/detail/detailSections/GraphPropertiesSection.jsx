import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import {
  localizeClaimPropertyKey,
  localizeMethodPropertyKey,
  localizeWorkPropertyKey,
} from "../../../model/graphLocalize.js";
import { formatPropertyValue } from "../detailFormatters.js";

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   t: (k: string, opts?: object) => string,
 *   detailPropertyEntries: Array<[string, unknown]>,
 *   claimNode: boolean,
 *   isMethodNode: boolean,
 * }} props
 */
export default function GraphPropertiesSection({ tk, t, detailPropertyEntries, claimNode, isMethodNode }) {
  return (
    <>
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.75, color: tk.text.primary }}>
        {t("graph.detailPanel.keyProperties")}
      </Typography>
      {detailPropertyEntries.length > 0 ? (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5, mb: 1 }}>
          {detailPropertyEntries.map(([k, v]) => (
            <Box key={k} sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, alignItems: "baseline" }}>
              <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, minWidth: "7rem" }}>
                {claimNode ? localizeClaimPropertyKey(k, t) : isMethodNode ? localizeMethodPropertyKey(k, t) : localizeWorkPropertyKey(k, t)}
              </Typography>
              <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, flex: 1, wordBreak: "break-word" }}>
                {formatPropertyValue(v)}
              </Typography>
            </Box>
          ))}
        </Box>
      ) : (
        <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted, mb: 1 }}>{t("graph.detailPanel.noProperties")}</Typography>
      )}
    </>
  );
}
