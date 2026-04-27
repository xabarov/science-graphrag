/**
 * @param {number | null | undefined} value
 * @returns {string}
 */
function formatMetricValue(value) {
  return value == null || Number.isNaN(Number(value)) ? "—" : Number(value).toFixed(3);
}

/**
 * @param {Record<string, any>} args
 * @param {string} args.experimentId
 * @param {{ caseCount: number, passCount: number, failCount: number, avgNamesF1: number | null, avgArxivF1: number | null, avgDoiF1: number | null, avgRecall: number | null } | null} args.summary
 */
export function buildTradeoffCards({ experimentId, summary }) {
  if (!summary) return [];
  if (experimentId === "layer2_semantic") {
    const stability =
      summary.caseCount > 0 ? `${summary.passCount}/${summary.caseCount}` : String(summary.passCount || 0);
    return [
      {
        id: "quality",
        tone: "primary",
        labelKey: "benchmarkPage.analysis.tradeoff.quality",
        value: formatMetricValue(summary.avgRecall),
        captionKey: "benchmarkPage.analysis.tradeoff.layer2QualityCaption",
      },
      {
        id: "stability",
        tone: summary.failCount > 0 ? "danger" : "default",
        labelKey: "benchmarkPage.analysis.tradeoff.stability",
        value: stability,
        captionKey: "benchmarkPage.analysis.tradeoff.stabilityCaption",
      },
    ];
  }
  return [
    {
      id: "quality",
      tone: "primary",
      labelKey: "benchmarkPage.analysis.tradeoff.quality",
      value: formatMetricValue(summary.avgNamesF1),
      captionKey: "benchmarkPage.analysis.tradeoff.layer1QualityCaption",
    },
    {
      id: "stability",
      tone: summary.failCount > 0 ? "danger" : "default",
      labelKey: "benchmarkPage.analysis.tradeoff.stability",
      value: String(summary.failCount || 0),
      captionKey: "benchmarkPage.analysis.tradeoff.failedCountCaption",
    },
  ];
}

/**
 * @param {{ baselineSummary: any, currentSummary: any }} args
 */
export function summarizeTradeoffDirection({ baselineSummary, currentSummary }) {
  if (!baselineSummary || !currentSummary) {
    return {
      tone: "default",
      labelKey: "benchmarkPage.analysis.tradeoff.insufficient",
    };
  }
  const qualityDelta =
    (currentSummary.avgRecall ?? currentSummary.avgNamesF1 ?? 0) -
    (baselineSummary.avgRecall ?? baselineSummary.avgNamesF1 ?? 0);
  const failDelta = (currentSummary.failCount ?? 0) - (baselineSummary.failCount ?? 0);
  if (qualityDelta > 0.0005 && failDelta <= 0) {
    return { tone: "primary", labelKey: "benchmarkPage.analysis.tradeoff.betterQuality" };
  }
  if (qualityDelta < -0.0005 && failDelta > 0) {
    return { tone: "danger", labelKey: "benchmarkPage.analysis.tradeoff.worseStability" };
  }
  return { tone: "default", labelKey: "benchmarkPage.analysis.tradeoff.mixed" };
}
