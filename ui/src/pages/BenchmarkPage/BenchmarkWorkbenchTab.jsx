import React, { useCallback, useEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { getBenchmarkRunCasesPage, getBenchmarkRunSummary, listBenchmarkRuns } from "../../services/benchmarkApi.js";
import { CursorButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import BenchmarkCaseInspectorShell from "./caseInspector/BenchmarkCaseInspectorShell.jsx";
import { useBenchmarkCaseInspectorData } from "./caseInspector/useBenchmarkCaseInspectorData.js";
import { WorkbenchRunScopedPanel } from "./workbench/BenchmarkWorkbenchRunPanel.jsx";

/**
 * @param {object} props
 * @param {string | null} props.selectedRunId
 * @param {string | null} props.selectedCaseId
 * @param {(runId: string | null) => void} [props.onSelectRun]
 * @param {(caseId: string | null) => void} [props.onSelectCase]
 * @param {string} [props.caseFamily]
 * @param {{ baselineRunId: string, metric: string } | null} [props.compareContext]
 */
export default function BenchmarkWorkbenchTab({
  selectedRunId,
  selectedCaseId,
  onSelectRun,
  onSelectCase,
  caseFamily = "layer1",
  compareContext = null,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const [runsPayload, setRunsPayload] = useState(null);
  const [runDetail, setRunDetail] = useState(null);
  const [runsError, setRunsError] = useState(null);
  const inspector = useBenchmarkCaseInspectorData({
    selectedRunId,
    selectedCaseId,
    caseFamily: (caseFamily || "layer1").trim().toLowerCase(),
  });

  const selectedCaseIdRef = useRef(selectedCaseId);
  useEffect(() => {
    selectedCaseIdRef.current = selectedCaseId;
  }, [selectedCaseId]);

  useEffect(() => {
    let cancelled = false;
    async function loadRuns() {
      try {
        const resp = await listBenchmarkRuns();
        if (!cancelled) setRunsPayload(resp);
      } catch (e) {
        if (!cancelled) setRunsError(e?.message || "failed_to_load_runs");
      }
    }
    loadRuns();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function loadRunDetail() {
      if (!selectedRunId) {
        setRunDetail(null);
        return;
      }
      setRunDetail(null);
      try {
        const resp = await getBenchmarkRunSummary(selectedRunId);
        let payload = resp?.data || resp;
        if (payload?.cases_paginated && selectedRunId) {
          try {
            const pr = await getBenchmarkRunCasesPage(selectedRunId, { offset: 0, limit: 500 });
            const pg = pr?.data || pr;
            const items = pg.items || [];
            const total = pg.total ?? payload.cases_total ?? items.length;
            payload = {
              ...payload,
              cases: items,
              cases_total: total,
              cases_paginated: items.length < total,
            };
          } catch {
            /* keep summary without cases rows */
          }
        }
        if (cancelled) return;
        setRunDetail(payload);
        const firstCase = payload?.cases?.[0]?.case_id || null;
        if (firstCase && !selectedCaseIdRef.current) onSelectCase?.(firstCase);
      } catch (e) {
        if (!cancelled) setRunsError(e?.message || "failed_to_load_run");
      }
    }
    loadRunDetail();
    return () => {
      cancelled = true;
    };
  }, [selectedRunId, onSelectCase]);

  const runItems = runsPayload?.items || [];
  const fixtureOnly = Boolean(!selectedRunId && selectedCaseId);
  const showRunPanel = Boolean(selectedRunId && runDetail);

  const openRunFromEvidence = useCallback(
    (rid) => {
      if (rid) onSelectRun?.(rid);
    },
    [onSelectRun],
  );

  const combinedError = runsError || inspector.error;

  return (
    <Box sx={{ padding: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap", mb: 2 }}>
        <Typography sx={{ fontWeight: 600 }}>{t("benchmark.workbench.pageTitle")}</Typography>
        <Select
          size="small"
          value={selectedRunId || ""}
          displayEmpty
          onChange={(e) => {
            onSelectRun?.(e.target.value || null);
            onSelectCase?.(null);
          }}
          sx={{ minWidth: 280 }}
        >
          <MenuItem value="">{t("benchmark.workbench.selectRun")}</MenuItem>
          {runItems.map((item) => (
            <MenuItem key={item.run_id} value={item.run_id}>
              {item.run_id.slice(0, 8)}... | {item.benchmark_family} | {item.status}
            </MenuItem>
          ))}
        </Select>
        <CursorButton onClick={() => window.location.reload()}>{t("benchmark.workbench.reload")}</CursorButton>
      </Box>

      {combinedError ? (
        <Typography sx={{ color: tk.state.dangerFg, mb: 2 }} role="alert">
          {combinedError}
        </Typography>
      ) : null}

      {!selectedRunId && !selectedCaseId ? (
        <Typography sx={{ color: tk.text.secondary }}>{t("benchmark.workbench.pickRun")}</Typography>
      ) : null}

      {fixtureOnly ? (
        <BenchmarkCaseInspectorShell
          mode="fixture"
          family={(caseFamily || "layer1").trim().toLowerCase()}
          caseId={selectedCaseId}
          caseDetail={inspector.caseDetail}
          fixtureDetail={inspector.fixtureDetail}
          compareContext={null}
          loading={inspector.loading}
          onOpenRun={openRunFromEvidence}
        />
      ) : null}

      {selectedRunId && !runDetail ? (
        <Typography sx={{ color: tk.text.secondary }}>{t("benchmark.workbench.loadingRun")}</Typography>
      ) : null}

      {showRunPanel ? (
        <WorkbenchRunScopedPanel
          key={selectedRunId}
          runDetail={runDetail}
          caseDetail={inspector.caseDetail}
          selectedCaseId={selectedCaseId}
          onSelectCase={onSelectCase}
          compareContext={compareContext}
          inspectorLoading={inspector.loading}
          onOpenRunFromEvidence={openRunFromEvidence}
          fixtureDetail={inspector.fixtureDetail}
        />
      ) : null}
    </Box>
  );
}
