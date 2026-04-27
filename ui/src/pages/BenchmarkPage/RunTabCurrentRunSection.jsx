import React from "react";
import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorButton } from "../../components/common/index.js";
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
}) {
  const tk = useTheme().appTokens;
  return (
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
  );
}
