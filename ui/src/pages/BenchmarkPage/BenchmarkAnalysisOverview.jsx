import React from "react";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorButton, CursorPrimaryButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";

import BenchmarkVariantMatrix from "./BenchmarkVariantMatrix.jsx";
import BenchmarkScorecardMetricSections from "./BenchmarkScorecardMetricSections.jsx";
import CompareDeltaTable from "./CompareDeltaTable.jsx";
import CompareTabSummarySection from "./CompareTabSummarySection.jsx";
import { buildTradeoffCards, summarizeTradeoffDirection } from "./benchmarkTradeoffModel.js";

function SummaryStat({ label, value }) {
  const tk = useTheme().appTokens;
  return (
    <Box
      sx={{
        border: `1px solid ${tk.border.default}`,
        borderRadius: 1.5,
        p: 1.5,
        backgroundColor: tk.surface.panel,
      }}
    >
      <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary }}>{label}</Typography>
      <Typography sx={{ mt: 0.25, fontWeight: 600, color: tk.text.primary }}>{value}</Typography>
    </Box>
  );
}

function TradeoffCard({ label, value, caption, tone = "default" }) {
  const tk = useTheme().appTokens;
  const color =
    tone === "danger" ? tk.state.dangerFg : tone === "primary" ? tk.accent.fg : tk.text.primary;
  return (
    <Box
      sx={{
        border: `1px solid ${tk.border.default}`,
        borderRadius: 1.5,
        p: 1.5,
        backgroundColor: tk.surface.panel,
      }}
    >
      <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary }}>{label}</Typography>
      <Typography sx={{ mt: 0.35, fontWeight: 600, color }}>{value}</Typography>
      <Typography sx={{ mt: 0.5, fontSize: "0.75rem", color: tk.text.secondary, lineHeight: 1.5 }}>{caption}</Typography>
    </Box>
  );
}

/**
 * @param {{ session: Record<string, any> | null, loading: boolean, error: Error | null, onReload: () => void, selectedExperimentId: string | null, selectedVariantId: string | null, selectedRow: Record<string, any> | null, selectedCell: Record<string, any> | null, onSelectCell: (experimentId: string, variantId: string) => void, compareResult: Record<string, any> | null, compareLoading: boolean, compareError: string | null, compareCurrentRunId: string | null, onOpenWorkbench: (runId: string, caseId?: string | null) => void, onOpenCompare: () => void, onOpenResults: () => void }} props
 */
export default function BenchmarkAnalysisOverview({
  session,
  loading,
  error,
  onReload,
  selectedExperimentId,
  selectedVariantId,
  selectedRow,
  selectedCell,
  onSelectCell,
  compareResult,
  compareLoading,
  compareError,
  compareCurrentRunId,
  onOpenWorkbench,
  onOpenCompare,
  onOpenResults,
}) {
  const tk = useTheme().appTokens;
  const { t } = useI18n();

  if (loading) {
    return (
      <Box sx={{ p: 2, display: "flex", alignItems: "center", gap: 1.25 }}>
        <CircularProgress size={18} />
        <Typography sx={{ color: tk.text.secondary }}>{t("benchmarkPage.analysis.loading")}</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box
        sx={{
          p: 2,
          border: `1px solid ${tk.border.default}`,
          borderRadius: 1.5,
          backgroundColor: tk.surface.panel,
        }}
      >
        <Typography sx={{ color: tk.state.dangerFg, mb: 1 }}>{error.message}</Typography>
        <CursorButton onClick={onReload}>{t("benchmarkPage.analysis.reload")}</CursorButton>
      </Box>
    );
  }

  if (!session?.rows?.length) {
    return (
      <Box
        sx={{
          p: 2,
          border: `1px solid ${tk.border.default}`,
          borderRadius: 1.5,
          backgroundColor: tk.surface.panel,
        }}
      >
        <Typography sx={{ fontWeight: 600, color: tk.text.primary }}>{t("benchmarkPage.analysis.emptyTitle")}</Typography>
        <Typography sx={{ mt: 0.75, color: tk.text.secondary, lineHeight: 1.6 }}>
          {t("benchmarkPage.analysis.emptyBody")}
        </Typography>
      </Box>
    );
  }

  const baselineCell = selectedRow?.variants?.find((item) => item.isBaseline) || null;
  const tradeoffCards = buildTradeoffCards({
    experimentId: selectedRow?.experimentId || "",
    summary: selectedCell?.summary || null,
  });
  const tradeoffDirection = summarizeTradeoffDirection({
    baselineSummary: baselineCell?.summary || null,
    currentSummary: selectedCell?.summary || null,
  });
  const topRegressions = Array.isArray(compareResult?.regressions) ? compareResult.regressions.slice(0, 10) : [];

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2, p: 2 }}>
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 1 }}>
        <SummaryStat label={t("benchmarkPage.analysis.summary.runSet")} value={session.runIds.length} />
        <SummaryStat label={t("benchmarkPage.analysis.summary.experiments")} value={session.rows.length} />
        <SummaryStat label={t("benchmarkPage.analysis.summary.variants")} value={session.variantIds.length} />
        <SummaryStat label={t("benchmarkPage.analysis.summary.source")} value={t(`benchmarkPage.analysis.source.${session.source}`)} />
      </Box>

      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1, flexWrap: "wrap" }}>
        <Box>
          <Typography sx={{ fontWeight: 600, color: tk.text.primary }}>{t("benchmarkPage.analysis.overviewTitle")}</Typography>
          <Typography sx={{ mt: 0.5, color: tk.text.secondary, fontSize: "0.8125rem", lineHeight: 1.55 }}>
            {t("benchmarkPage.analysis.overviewBody")}
          </Typography>
        </Box>
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          <CursorPrimaryButton onClick={onOpenCompare} disabled={!compareCurrentRunId}>
            {t("benchmarkPage.analysis.openCompare")}
          </CursorPrimaryButton>
          <CursorButton onClick={onOpenResults}>{t("benchmarkPage.analysis.openResults")}</CursorButton>
        </Box>
      </Box>

      <BenchmarkVariantMatrix
        session={session}
        selectedExperimentId={selectedExperimentId}
        selectedVariantId={selectedVariantId}
        onSelectCell={onSelectCell}
        onOpenWorkbench={(runId) => onOpenWorkbench(runId, null)}
      />

      <Box sx={{ display: "grid", gridTemplateColumns: "minmax(0, 1.3fr) minmax(320px, 0.9fr)", gap: 2 }}>
        <Box
          sx={{
            border: `1px solid ${tk.border.default}`,
            borderRadius: 1.5,
            p: 1.75,
            backgroundColor: tk.surface.panel,
          }}
        >
          <Typography sx={{ fontWeight: 600, color: tk.text.primary }}>
            {selectedRow ? t(selectedRow.experiment.titleKey) : t("benchmarkPage.analysis.selectionTitle")}
          </Typography>
          <Typography sx={{ mt: 0.5, color: tk.text.secondary, fontSize: "0.8125rem", lineHeight: 1.55 }}>
            {selectedRow ? t(selectedRow.experiment.descriptionKey) : t("benchmarkPage.analysis.selectionHint")}
          </Typography>

          {selectedCell ? (
            <>
              <Box sx={{ mt: 1.5, display: "flex", flexWrap: "wrap", gap: 1 }}>
                <SummaryStat label={t("benchmarkPage.analysis.selection.variant")} value={selectedCell.variantLabel} />
                <SummaryStat
                  label={t("benchmarkPage.analysis.selection.baseline")}
                  value={baselineCell?.variantLabel || t("benchmarkPage.analysis.matrix.missing")}
                />
                <SummaryStat label={t("benchmarkPage.analysis.selection.tradeoff")} value={t(tradeoffDirection.labelKey)} />
              </Box>
              <Box sx={{ mt: 1.5, display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 1 }}>
                {tradeoffCards.map((card) => (
                  <TradeoffCard
                    key={card.id}
                    label={t(card.labelKey)}
                    value={card.value}
                    caption={t(card.captionKey)}
                    tone={card.tone}
                  />
                ))}
              </Box>
              {selectedCell?.scorecard &&
              (Object.keys(selectedCell.scorecard.secondary || {}).length > 0 ||
                Object.keys(selectedCell.scorecard.diagnostic || {}).length > 0) ? (
                <BenchmarkScorecardMetricSections
                  titleSecondary={t("benchmarkPage.analysis.scorecard.secondaryTitle")}
                  titleDiagnostic={t("benchmarkPage.analysis.scorecard.diagnosticTitle")}
                  secondary={selectedCell.scorecard.secondary}
                  diagnostic={selectedCell.scorecard.diagnostic}
                  tk={tk}
                />
              ) : null}
            </>
          ) : null}
        </Box>

        <Box
          sx={{
            border: `1px solid ${tk.border.default}`,
            borderRadius: 1.5,
            p: 1.75,
            backgroundColor: tk.surface.panel,
          }}
        >
          <Typography sx={{ fontWeight: 600, color: tk.text.primary }}>{t("benchmarkPage.analysis.groupDetailTitle")}</Typography>
          <Typography sx={{ mt: 0.5, color: tk.text.secondary, fontSize: "0.8125rem", lineHeight: 1.55 }}>
            {t("benchmarkPage.analysis.groupDetailBody")}
          </Typography>
          <Box sx={{ mt: 1.5, display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 1 }}>
            <SummaryStat
              label={t("benchmarkPage.analysis.group.experiments")}
              value={session.rows.map((row) => t(row.experiment.titleKey)).join(", ")}
            />
            <SummaryStat label={t("benchmarkPage.analysis.group.variants")} value={session.variantIds.join(", ")} />
          </Box>
          {session.runIds?.length ? (
            <Box sx={{ mt: 1 }}>
              <SummaryStat label={t("benchmarkPage.analysis.group.runIds")} value={session.runIds.join(", ")} />
            </Box>
          ) : null}
        </Box>
      </Box>

      <Box
        sx={{
          border: `1px solid ${tk.border.default}`,
          borderRadius: 1.5,
          p: 1.75,
          backgroundColor: tk.surface.panel,
        }}
      >
        <Typography sx={{ fontWeight: 600, color: tk.text.primary }}>{t("benchmarkPage.analysis.deltaTitle")}</Typography>
        <Typography sx={{ mt: 0.5, color: tk.text.secondary, fontSize: "0.8125rem", lineHeight: 1.55 }}>
          {t("benchmarkPage.analysis.deltaBody")}
        </Typography>
        {compareLoading ? (
          <Typography sx={{ mt: 1.5, color: tk.text.secondary }}>{t("benchmarkPage.analysis.compareLoading")}</Typography>
        ) : null}
        {compareError ? (
          <Typography sx={{ mt: 1.5, color: tk.state.dangerFg }}>{compareError}</Typography>
        ) : null}
        {compareResult?.summary ? <Box sx={{ mt: 1.5 }}><CompareTabSummarySection summary={compareResult.summary} result={compareResult} /></Box> : null}
        {compareResult ? (
          <Box sx={{ mt: 1 }}>
            <CompareDeltaTable
              title={t("benchmarkPage.analysis.topRegressions")}
              rows={topRegressions}
              onOpenCase={onOpenWorkbench}
              currentRunId={compareCurrentRunId}
            />
          </Box>
        ) : null}
      </Box>
    </Box>
  );
}
