import React, { useMemo } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../../i18n/useI18n.js";

import { getHighlightsOrFallback } from "./benchmarkCaseInspectorModel.js";
import BenchmarkCaseInspectorEvidencePanel from "./BenchmarkCaseInspectorEvidencePanel.jsx";
import BenchmarkCaseInspectorHeader from "./BenchmarkCaseInspectorHeader.jsx";
import BenchmarkCaseInspectorHeadlineSection from "./BenchmarkCaseInspectorHeadlineSection.jsx";
import BenchmarkCaseInspectorRawAccordion from "./BenchmarkCaseInspectorRawAccordion.jsx";
import { renderFamilyInspectorPanel } from "./caseInspectorRegistry.jsx";

/**
 * @param {{
 *   mode: "run" | "fixture",
 *   family: string,
 *   caseId: string | null,
 *   caseDetail: Record<string, unknown> | null,
 *   fixtureDetail: Record<string, unknown> | null,
 *   compareContext: { baselineRunId: string; metric: string } | null,
 *   loading?: boolean,
 *   onOpenRun: (runId: string) => void,
 * }} props
 */
export default function BenchmarkCaseInspectorShell({
  mode,
  family,
  caseId,
  caseDetail,
  fixtureDetail,
  compareContext,
  loading = false,
  onOpenRun,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;

  const highlights = useMemo(() => getHighlightsOrFallback(caseDetail), [caseDetail]);
  const headline =
    mode === "fixture" && !(highlights.headline && String(highlights.headline).trim())
      ? t("benchmark.inspector.fixtureHeadline")
      : String(highlights.headline || "");
  const issues = useMemo(
    () => (Array.isArray(highlights.issues) ? highlights.issues : []),
    [highlights.issues],
  );
  const evidenceLinks = Array.isArray(caseDetail?.evidence_links) ? caseDetail.evidence_links : [];

  const comparisonRows = useMemo(() => {
    const comp = /** @type {Record<string, unknown>} */ (caseDetail?.comparison || {});
    return (
      (Array.isArray(comp.metadata_rows) && comp.metadata_rows) ||
      (Array.isArray(comp.method_rows) && comp.method_rows) ||
      []
    );
  }, [caseDetail]);

  const headlineSeverity = useMemo(() => {
    const hasError = issues.some(
      (i) => i && typeof i === "object" && /** @type {Record<string, unknown>} */ (i).severity === "error",
    );
    if (hasError) return "error";
    if (issues.length) return "warning";
    return "success";
  }, [issues]);

  if (loading && !caseDetail) {
    return (
      <Typography sx={{ color: tk.text.secondary, fontSize: "0.8125rem" }}>{t("benchmark.inspector.loading")}</Typography>
    );
  }

  if (!caseDetail) {
    return (
      <Typography sx={{ color: tk.text.secondary, fontSize: "0.8125rem" }}>{t("benchmark.workbench.selectCase")}</Typography>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <BenchmarkCaseInspectorHeader
        tk={tk}
        title={t("benchmark.inspector.title")}
        caseId={caseId}
        mode={mode}
        family={family}
        caseDetail={caseDetail}
      />

      <BenchmarkCaseInspectorHeadlineSection
        tk={tk}
        compareContext={compareContext}
        headline={headline}
        headlineSeverity={headlineSeverity}
        issues={issues}
        t={t}
      />

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "minmax(0, 1.4fr) minmax(260px, 0.6fr)" },
          gap: 2,
          alignItems: "start",
        }}
      >
        <Box
          sx={{
            border: `1px solid ${tk.border.default}`,
            borderRadius: 1.5,
            backgroundColor: tk.surface.panel,
            p: 1.5,
          }}
        >
          {renderFamilyInspectorPanel({
            family,
            caseDetail,
            fixtureDetail,
            caseId,
          })}
        </Box>

        <BenchmarkCaseInspectorEvidencePanel tk={tk} evidenceLinks={evidenceLinks} onOpenRun={onOpenRun} t={t} />
      </Box>

      <BenchmarkCaseInspectorRawAccordion tk={tk} caseDetail={caseDetail} comparisonRows={comparisonRows} t={t} />
    </Box>
  );
}
