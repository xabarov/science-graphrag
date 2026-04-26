import React, { useEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";

import {
  getBenchmarkRunCaseDetail,
  getBenchmarkRunCasesPage,
  getBenchmarkRunSummary,
  listBenchmarkRuns,
} from "../../services/benchmarkApi.js";
import { CursorButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { WorkbenchRunScopedPanel } from "./workbench/BenchmarkWorkbenchRunPanel.jsx";

export default function BenchmarkWorkbenchTab({
  selectedRunId,
  selectedCaseId,
  onSelectRun,
  onSelectCase,
}) {
  const { t } = useI18n();
  const [runsPayload, setRunsPayload] = useState(null);
  const [runDetail, setRunDetail] = useState(null);
  const [caseDetail, setCaseDetail] = useState(null);
  const [error, setError] = useState(null);
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
        if (!cancelled) setError(e?.message || "failed_to_load_runs");
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
        if (!cancelled) setError(e?.message || "failed_to_load_run");
      }
    }
    loadRunDetail();
    return () => {
      cancelled = true;
    };
  }, [selectedRunId, onSelectCase]);

  useEffect(() => {
    let cancelled = false;
    async function loadCaseDetail() {
      if (!selectedRunId || !selectedCaseId) {
        setCaseDetail(null);
        return;
      }
      try {
        const resp = await getBenchmarkRunCaseDetail(selectedRunId, selectedCaseId);
        if (!cancelled) setCaseDetail(resp?.data || resp);
      } catch (e) {
        if (!cancelled) setError(e?.message || "failed_to_load_case_detail");
      }
    }
    loadCaseDetail();
    return () => {
      cancelled = true;
    };
  }, [selectedRunId, selectedCaseId]);

  const runItems = runsPayload?.items || [];

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

      {error ? (
        <Typography sx={{ color: "rgba(239,68,68,0.9)", mb: 2 }} role="alert">
          {error}
        </Typography>
      ) : null}

      {!selectedRunId ? (
        <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>{t("benchmark.workbench.pickRun")}</Typography>
      ) : !runDetail ? (
        <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>{t("benchmark.workbench.loadingRun")}</Typography>
      ) : (
        <WorkbenchRunScopedPanel
          key={selectedRunId}
          runDetail={runDetail}
          caseDetail={caseDetail}
          selectedCaseId={selectedCaseId}
          onSelectCase={onSelectCase}
        />
      )}
    </Box>
  );
}
