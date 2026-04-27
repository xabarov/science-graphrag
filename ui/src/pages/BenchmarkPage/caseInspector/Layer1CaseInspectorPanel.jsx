import React, { useMemo } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../../i18n/useI18n.js";

/**
 * @param {{ caseDetail: Record<string, unknown> | null }} props
 */
export default function Layer1CaseInspectorPanel({ caseDetail }) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const summary = /** @type {Record<string, unknown>} */ (caseDetail?.summary || {});
  const metrics = /** @type {Record<string, unknown>} */ (caseDetail?.metrics || {});
  const auth = /** @type {Record<string, unknown>} */ (metrics.authorships || {});
  const refs = /** @type {Record<string, unknown>} */ (metrics.references || {});

  const metaRows = useMemo(() => {
    const comp = /** @type {Record<string, unknown>} */ (caseDetail?.comparison || {});
    return Array.isArray(comp.metadata_rows) ? comp.metadata_rows : [];
  }, [caseDetail]);

  const mismatchedFields = useMemo(
    () =>
      metaRows
        .filter((row) => {
          if (!row || typeof row !== "object") return false;
          const r = /** @type {Record<string, unknown>} */ (row);
          return r.gold_value !== r.predicted_value;
        })
        .map((row) => String(/** @type {Record<string, unknown>} */ (row).field || ""))
        .filter(Boolean),
    [metaRows],
  );

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1.25 }}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>{t("benchmark.inspector.layer1.title")}</Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
        {summary.names_f1 != null ? (
          <Chip size="small" label={`names_f1 ${Number(summary.names_f1).toFixed(3)}`} variant="outlined" />
        ) : null}
        {summary.sample_arxiv_f1 != null ? (
          <Chip size="small" label={`arxiv_f1 ${Number(summary.sample_arxiv_f1).toFixed(3)}`} variant="outlined" />
        ) : null}
        {auth.names_f1 != null ? (
          <Chip size="small" label={`metrics.names_f1 ${Number(auth.names_f1).toFixed(3)}`} variant="outlined" />
        ) : null}
        {refs.sample_arxiv_f1 != null ? (
          <Chip size="small" label={`metrics.arxiv_f1 ${Number(refs.sample_arxiv_f1).toFixed(3)}`} variant="outlined" />
        ) : null}
      </Box>
      {mismatchedFields.length ? (
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary }}>
          {t("benchmark.inspector.layer1.metadataMismatches", { fields: mismatchedFields.join(", ") })}
        </Typography>
      ) : (
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted }}>{t("benchmark.inspector.layer1.metadataAligned")}</Typography>
      )}
    </Box>
  );
}
