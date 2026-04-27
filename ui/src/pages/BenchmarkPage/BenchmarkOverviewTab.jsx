import React, { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorSmallButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { listBenchmarkRuns } from "../../services/benchmarkApi.js";

import TrustSignalPanel from "./TrustSignalPanel.jsx";
import {
  benchmarkTypeLabelKey,
  compareModeLabelKey,
  getReportCriticalExperiments,
  runnableSurfaceLabelKey,
} from "./experimentCatalog.js";

/**
 * @param {object} props
 * @param {(opts: { tabIndex: number, analysisView?: "results"|"compare"|"workbench", experimentId?: string | null, runMode?: "single"|"grouped", packId?: string | null }) => void} props.onNavigate
 * @param {(runId: string, caseId?: string | null) => void} props.onOpenWorkbench
 */
export default function BenchmarkOverviewTab({ onNavigate, onOpenWorkbench }) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const [runs, setRuns] = useState(/** @type {unknown[]} */ ([]));
  const [runsError, setRunsError] = useState(/** @type {string | null} */ (null));
  const [runsLoading, setRunsLoading] = useState(true);

  async function loadRuns() {
    setRunsLoading(true);
    setRunsError(null);
    try {
      const resp = await listBenchmarkRuns({});
      const items = resp?.items || [];
      const list = Array.isArray(items) ? items.slice(0, 12) : [];
      setRuns(
        list.filter((row) => {
          const o = /** @type {Record<string, unknown>} */ (row);
          return Boolean(String(o.id ?? o.run_id ?? "").trim());
        }),
      );
      setRunsError(null);
    } catch (e) {
      setRunsError(e?.message || "failed_to_load_runs");
      setRuns([]);
    } finally {
      setRunsLoading(false);
    }
  }

  useEffect(() => {
    void loadRuns();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- initial overview fetch only
  }, []);

  const critical = getReportCriticalExperiments();

  return (
    <Box sx={{ p: 2, display: "flex", flexDirection: "column", gap: 2 }}>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
        <CursorSmallButton size="small" onClick={() => onNavigate({ tabIndex: 2 })}>
          {t("benchmarkPage.overview.openRunLab")}
        </CursorSmallButton>
        <CursorSmallButton size="small" onClick={() => onNavigate({ tabIndex: 3, analysisView: "results" })}>
          {t("benchmarkPage.overview.openAnalysis")}
        </CursorSmallButton>
        <CursorSmallButton size="small" onClick={() => onNavigate({ tabIndex: 1 })}>
          {t("benchmarkPage.overview.openExperiments")}
        </CursorSmallButton>
      </Box>

      <Box>
        <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", mb: 1 }}>{t("benchmarkPage.overview.reportCriticalTitle")}</Typography>
        <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 1 }}>
          {critical.map((exp) => (
            <Box
              key={exp.id}
              sx={{
                border: `1px solid ${tk.border.default}`,
                borderRadius: "6px",
                backgroundColor: tk.surface.panel,
                p: 1.5,
                display: "flex",
                flexDirection: "column",
                gap: 0.75,
              }}
            >
              <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: tk.text.primary }}>{t(exp.titleKey)}</Typography>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                <Chip size="small" label={t(benchmarkTypeLabelKey(exp.benchmarkType))} sx={{ height: 22, fontSize: "0.7rem" }} />
                <Chip size="small" label={t(runnableSurfaceLabelKey(exp.runnableSurface))} variant="outlined" sx={{ height: 22, fontSize: "0.7rem" }} />
              </Box>
              <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, lineHeight: 1.45 }}>{t(exp.descriptionKey)}</Typography>
              <Typography sx={{ fontSize: "0.7rem", color: tk.text.muted, fontWeight: 600 }}>
                {t("benchmarkPage.overview.primaryMetrics")}
              </Typography>
              <Typography sx={{ fontSize: "0.7rem", color: tk.text.secondary }}>
                {exp.primaryMetricKeys.map((k) => t(k)).join(" · ")}
              </Typography>
              <Typography sx={{ fontSize: "0.68rem", color: tk.text.muted }}>{t(compareModeLabelKey(exp.recommendedCompareMode))}</Typography>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 0.5 }}>
                {exp.runnableSurface === "ui" && exp.uiFamily ? (
                  <CursorSmallButton size="small" onClick={() => onNavigate({ tabIndex: 2, experimentId: exp.id })}>
                    {t("benchmarkPage.overview.openRunLab")}
                  </CursorSmallButton>
                ) : (
                  <Typography sx={{ fontSize: "0.68rem", color: tk.text.muted }}>
                    {t("benchmarkPage.experiments.notRunnableFromUi")}
                  </Typography>
                )}
                <CursorSmallButton size="small" onClick={() => onNavigate({ tabIndex: 3, analysisView: "results" })}>
                  {t("benchmarkPage.overview.openAnalysis")}
                </CursorSmallButton>
              </Box>
            </Box>
          ))}
        </Box>
      </Box>

      <Box>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1 }}>
          <Typography sx={{ fontWeight: 600, fontSize: "0.875rem" }}>{t("benchmarkPage.overview.recentRuns")}</Typography>
          <CursorSmallButton size="small" onClick={() => void loadRuns()}>
            {t("benchmarkPage.trustSignal.refresh")}
          </CursorSmallButton>
        </Box>
        {runsError ? (
          <Typography sx={{ color: tk.state.dangerFg, fontSize: "0.8125rem" }} role="alert">
            {runsError}
          </Typography>
        ) : runsLoading ? (
          <Typography sx={{ color: tk.text.muted, fontSize: "0.8125rem" }}>{t("benchmarkPage.overview.loadingRuns")}</Typography>
        ) : runs.length === 0 ? (
          <Typography sx={{ color: tk.text.secondary, fontSize: "0.8125rem" }}>{t("benchmarkPage.overview.recentRunsEmpty")}</Typography>
        ) : (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
            {runs.map((row, idx) => {
              const r = /** @type {Record<string, unknown>} */ (row);
              const id = String(r.id ?? r.run_id ?? "").trim();
              const fam = String(r.benchmark_family ?? r.family ?? "");
              const st = String(r.status ?? "");
              const idShort = id.length > 12 ? `${id.slice(0, 10)}…` : id;
              return (
                <Box
                  key={id || `run-${idx}`}
                  sx={{
                    display: "flex",
                    flexWrap: "wrap",
                    alignItems: "center",
                    gap: 1,
                    py: 0.5,
                    borderTop: `1px solid ${tk.border.default}`,
                  }}
                >
                  <Typography sx={{ fontFamily: "monospace", fontSize: "0.75rem", color: tk.text.primary }} title={id}>
                    {idShort}
                  </Typography>
                  <Chip size="small" label={fam || "?"} sx={{ height: 22, fontSize: "0.68rem" }} />
                  <Chip size="small" label={st || "?"} variant="outlined" sx={{ height: 22, fontSize: "0.68rem" }} />
                  <CursorSmallButton size="small" onClick={() => onOpenWorkbench(id, null)}>
                    {t("benchmarkPage.analysis.workbench")}
                  </CursorSmallButton>
                  <CursorSmallButton size="small" onClick={() => onNavigate({ tabIndex: 3, analysisView: "results" })}>
                    {t("benchmarkPage.analysis.results")}
                  </CursorSmallButton>
                </Box>
              );
            })}
          </Box>
        )}
      </Box>

      <Box
        sx={{
          border: `1px solid ${tk.border.default}`,
          borderRadius: "6px",
          backgroundColor: tk.surface.subtle,
          p: 1.5,
        }}
      >
        <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 1, color: tk.text.secondary }}>
          {t("benchmarkPage.overview.diagnosticsTitle")}
        </Typography>
        <TrustSignalPanel defaultExpanded={false} />
      </Box>
    </Box>
  );
}
