import React from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorButton, CursorSmallButton } from "../../components/common/index.js";
import BenchmarkRunConfigSummary from "./BenchmarkRunConfigSummary.jsx";

/**
 * @param {object} props
 * @param {(key: string, vars?: Record<string, string>) => string} props.t
 * @param {string | null} props.runId
 * @param {Record<string, unknown> | null} props.run
 * @param {number} props.progressPercent
 * @param {number} props.progressCompleted
 * @param {number} props.progressTotal
 * @param {Record<string, unknown> | null} props.currentRunSummary
 * @param {Record<string, unknown>} props.summary
 * @param {() => void} [props.onSwitchToResults]
 * @param {readonly string[]} props.terminalStatuses
 * @param {boolean} [props.showSingleRun]
 * @param {object | null} [props.groupProgress]
 * @param {string | null} [props.groupProgress.groupId]
 * @param {string} [props.groupProgress.aggregateStatus]
 * @param {Array<{ key: string, experimentId: string, family: string, modelProfileId: string, runId: string | null, status: string, error: string | null }>} [props.groupProgress.children]
 * @param {(runId: string) => void} [props.onSelectGroupRun]
 */

export default function RunTabCurrentRunSection({
  t,
  runId,
  run,
  progressPercent,
  progressCompleted,
  progressTotal,
  currentRunSummary,
  summary,
  onSwitchToResults,
  terminalStatuses,
  showSingleRun = true,
  groupProgress = null,
  onSelectGroupRun,
}) {
  const tk = useTheme().appTokens;
  const hasGroup = Boolean(groupProgress?.children?.length);
  const rawAggregate = groupProgress?.aggregateStatus;
  const aggregateI18nKey = rawAggregate ? `benchmarkPage.runLab.groupStatus.${rawAggregate}` : null;
  const aggregateTranslated = aggregateI18nKey ? t(aggregateI18nKey) : null;
  const aggregateLabel =
    rawAggregate && aggregateTranslated && aggregateTranslated !== aggregateI18nKey ? aggregateTranslated : rawAggregate || "—";

  return (
    <>
      {hasGroup ? (
        <Box sx={{ mb: 3 }}>
          <Typography sx={{ fontWeight: 600, mb: 1 }}>{t("benchmarkPage.runLab.groupProgress.title")}</Typography>
          <Typography sx={{ color: tk.text.secondary, fontSize: "0.75rem", mb: 1 }}>
            {t("benchmarkPage.runLab.groupProgress.aggregate", { status: aggregateLabel })}
          </Typography>
          {groupProgress.groupId ? (
            <Typography sx={{ color: tk.text.muted, fontSize: "0.68rem", fontFamily: "monospace", mb: 1 }}>
              {groupProgress.groupId}
            </Typography>
          ) : null}
          <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
            {groupProgress.children.map((c) => (
              <Box
                key={c.key}
                sx={{
                  display: "flex",
                  flexWrap: "wrap",
                  alignItems: "center",
                  gap: 0.75,
                  py: 0.5,
                  borderTop: `1px solid ${tk.border.default}`,
                }}
              >
                <Typography sx={{ fontSize: "0.75rem", fontWeight: 600 }}>{c.experimentId}</Typography>
                <Chip size="small" label={c.family} sx={{ height: 22, fontSize: "0.65rem" }} />
                <Chip size="small" label={c.modelProfileId} variant="outlined" sx={{ height: 22, fontSize: "0.65rem" }} />
                <Chip size="small" label={c.status} variant="outlined" sx={{ height: 22, fontSize: "0.65rem" }} />
                {c.runId ? (
                  <Typography sx={{ fontFamily: "monospace", fontSize: "0.68rem", color: tk.text.secondary }} title={c.runId}>
                    {c.runId.length > 14 ? `${c.runId.slice(0, 12)}…` : c.runId}
                  </Typography>
                ) : null}
                {c.error ? (
                  <Typography sx={{ fontSize: "0.68rem", color: tk.state.dangerFg, flex: "1 1 100%" }}>{c.error}</Typography>
                ) : null}
                {c.runId && onSelectGroupRun ? (
                  <CursorSmallButton size="small" onClick={() => onSelectGroupRun(c.runId)}>
                    {t("benchmarkPage.runLab.groupProgress.useRun")}
                  </CursorSmallButton>
                ) : null}
              </Box>
            ))}
          </Box>
        </Box>
      ) : null}

      {showSingleRun ? (
        <>
          <Typography sx={{ fontWeight: 600, mb: 1 }}>{t("benchmark.run.currentRun")}</Typography>
          {!runId ? (
            <Typography sx={{ color: tk.text.secondary }}>{t("benchmark.run.emptyRun")}</Typography>
          ) : (
            <Box>
              <Typography sx={{ color: tk.text.secondary, mb: 1 }}>
                {t("benchmark.run.runId")}{" "}
                <Box component="span" sx={{ color: tk.text.primary }}>
                  {runId}
                </Box>
              </Typography>

              <LinearProgress variant="determinate" value={progressPercent} />
              <Typography sx={{ color: tk.text.secondary, mt: 1 }}>
                {t("benchmark.run.progressLine", {
                  done: String(progressCompleted),
                  total: String(progressTotal),
                  pct: progressPercent.toFixed(1),
                })}
              </Typography>

              {currentRunSummary ? <BenchmarkRunConfigSummary summary={currentRunSummary} title={t("benchmark.run.configTitle")} /> : null}

              {run && (
                <Box sx={{ mt: 1, display: "flex", gap: 2, flexWrap: "wrap" }}>
                  {(run.benchmark_family || "layer1") === "layer2" ? (
                    <Typography sx={{ color: tk.text.secondary }}>
                      {t("benchmark.run.metricLayer2", { v: (summary.avg_layer2_recall_ratio ?? 0).toFixed(3) })}
                    </Typography>
                  ) : (
                    <>
                      <Typography sx={{ color: tk.text.secondary }}>
                        {t("benchmark.run.metricNames", { v: (summary.avg_names_f1 ?? 0).toFixed(3) })}
                      </Typography>
                      <Typography sx={{ color: tk.text.secondary }}>
                        {t("benchmark.run.metricArxiv", { v: (summary.avg_sample_arxiv_f1 ?? 0).toFixed(3) })}
                      </Typography>
                    </>
                  )}
                </Box>
              )}

              <Box sx={{ mt: 2 }}>
                <CursorButton disabled={!run || !terminalStatuses.includes(run.status)} onClick={() => onSwitchToResults?.()}>
                  {t("benchmark.run.openResults")}
                </CursorButton>
              </Box>
            </Box>
          )}
        </>
      ) : (
        <Typography sx={{ color: tk.text.muted, fontSize: "0.8125rem" }}>{t("benchmarkPage.runLab.groupProgress.singleHidden")}</Typography>
      )}
    </>
  );
}
