import React, { useMemo } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../../i18n/useI18n.js";

/**
 * @param {{ caseDetail: Record<string, unknown> | null }} props
 */
export default function Layer2CaseInspectorPanel({ caseDetail }) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const summary = /** @type {Record<string, unknown>} */ (caseDetail?.summary || {});

  const { misses, extras } = useMemo(() => {
    const comp = /** @type {Record<string, unknown>} */ (caseDetail?.comparison || {});
    const rows = Array.isArray(comp.method_rows) ? comp.method_rows : [];
    const miss = rows.filter((r) => r && typeof r === "object" && /** @type {Record<string, unknown>} */ (r).status === "miss");
    const extra = rows.filter((r) => r && typeof r === "object" && /** @type {Record<string, unknown>} */ (r).status === "extra");
    return { misses: miss, extras: extra };
  }, [caseDetail]);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1.25 }}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>{t("benchmark.inspector.layer2.title")}</Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
        {summary.precision_methods != null ? (
          <Chip size="small" label={`p_methods ${Number(summary.precision_methods).toFixed(2)}`} variant="outlined" />
        ) : null}
        {summary.layer2_recall_ratio != null ? (
          <Chip size="small" label={`L2 recall ${Number(summary.layer2_recall_ratio).toFixed(3)}`} variant="outlined" />
        ) : null}
        <Chip
          size="small"
          color={misses.length ? "warning" : "default"}
          label={t("benchmark.inspector.layer2.missCount", { count: String(misses.length) })}
          variant="outlined"
        />
        <Chip
          size="small"
          color={extras.length ? "info" : "default"}
          label={t("benchmark.inspector.layer2.extraCount", { count: String(extras.length) })}
          variant="outlined"
        />
      </Box>
      {misses.length ? (
        <Box>
          <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, mb: 0.5 }}>{t("benchmark.inspector.layer2.missSample")}</Typography>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
            {misses.slice(0, 12).map((row, idx) => (
              <Chip
                key={`m-${idx}`}
                size="small"
                label={String(/** @type {Record<string, unknown>} */ (row).value || "")}
                sx={{ fontSize: "0.7rem" }}
              />
            ))}
          </Box>
        </Box>
      ) : null}
    </Box>
  );
}
