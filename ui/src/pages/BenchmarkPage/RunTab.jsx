import React, { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormGroup from "@mui/material/FormGroup";
import LinearProgress from "@mui/material/LinearProgress";
import Divider from "@mui/material/Divider";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import Alert from "@mui/material/Alert";

import { listBenchmarkCases, getBenchmarkRun, runBenchmark } from "../../services/benchmarkApi.js";
import { CursorButton, CursorPrimaryButton } from "../../components/common/index.js";

const TERMINAL_STATUSES = ["completed", "failed", "cancelled"];

function _toggleCase(prev, caseId) {
  if (prev.includes(caseId)) return prev.filter((x) => x !== caseId);
  return [...prev, caseId];
}

export default function RunTab({ onSwitchToResults }) {
  const [benchmarkFamily, setBenchmarkFamily] = useState("layer1");
  const [mergeSafeCases, setMergeSafeCases] = useState([]);
  const [nightlyCases, setNightlyCases] = useState([]);
  const [selectedCaseIds, setSelectedCaseIds] = useState([]);

  const [runId, setRunId] = useState(() => window.localStorage.getItem("benchmark:lastRunId") || null);
  const [run, setRun] = useState(null);
  const [error, setError] = useState(null);
  const [loadingCases, setLoadingCases] = useState(false);

  const progressPercent = run?.progress?.percent ?? 0;
  const progressCompleted = run?.progress?.completed ?? 0;
  const progressTotal = run?.progress?.total ?? 0;

  const summary = run?.summary || {};
  const nightlyTierParam =
    benchmarkFamily === "layer2" ? "nightly_semantic" : "nightly_heavy";
  const nightlyLabel =
    benchmarkFamily === "layer2" ? "nightly_semantic" : "nightly_heavy";
  const isGraphCatalog = benchmarkFamily === "graph";

  useEffect(() => {
    setSelectedCaseIds([]);
  }, [benchmarkFamily]);

  useEffect(() => {
    let cancelled = false;
    async function loadCases() {
      setLoadingCases(true);
      try {
        const fam = benchmarkFamily === "graph" ? "graph" : benchmarkFamily;
        const [merge, nightly] = await Promise.all([
          listBenchmarkCases({ family: fam, tier: "merge_safe" }),
          listBenchmarkCases({ family: fam, tier: nightlyTierParam }),
        ]);
        if (cancelled) return;
        setMergeSafeCases(merge?.items || []);
        setNightlyCases(nightly?.items || []);
      } catch (e) {
        if (!cancelled) setError(e?.message || "failed_to_load_cases");
      } finally {
        if (!cancelled) setLoadingCases(false);
      }
    }
    loadCases();
    return () => {
      cancelled = true;
    };
  }, [benchmarkFamily, nightlyTierParam]);

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    let intervalId = null;

    async function tick() {
      try {
        const resp = await getBenchmarkRun(runId);
        const payload = resp?.data || resp;
        if (cancelled) return;
        setRun(payload);

        const status = payload?.status;
        if (TERMINAL_STATUSES.includes(status)) {
          if (intervalId) clearInterval(intervalId);
        }
      } catch (e) {
        if (!cancelled) setError(e?.message || "failed_to_fetch_run");
      }
    }

    tick();
    intervalId = window.setInterval(tick, 2000);
    return () => {
      cancelled = true;
      if (intervalId) clearInterval(intervalId);
    };
  }, [runId]);

  async function startRun({ caseSelector, label }) {
    if (isGraphCatalog) return;
    setError(null);
    const res = await runBenchmark({ case_ids: caseSelector, label, family: benchmarkFamily });
    const newRunId = res?.run_id;
    if (!newRunId) throw new Error("run_id_missing");
    window.localStorage.setItem("benchmark:lastRunId", newRunId);
    setRunId(newRunId);
  }

  const selectedSet = useMemo(() => new Set(selectedCaseIds), [selectedCaseIds]);

  const title = isGraphCatalog
    ? "Graph-v1 cases (catalog only)"
    : benchmarkFamily === "layer2"
      ? "Запуск Layer-2 (semantic) Benchmark"
      : "Запуск Layer-1 Benchmark";

  return (
    <Box sx={{ padding: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap", mb: 2 }}>
        <Typography sx={{ fontWeight: 600 }}>{title}</Typography>
        <Select
          size="small"
          value={benchmarkFamily}
          onChange={(e) => setBenchmarkFamily(e.target.value)}
          sx={{ minWidth: 140 }}
        >
          <MenuItem value="layer1">layer1</MenuItem>
          <MenuItem value="layer2">layer2</MenuItem>
          <MenuItem value="graph">graph (CLI)</MenuItem>
        </Select>
      </Box>

      {isGraphCatalog ? (
        <Alert severity="info" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          Graph-v1 runs ingest into Neo4j/Qdrant and are not started from this UI. Use:{" "}
          <code>science-graphrag-graph-benchmark tests/fixtures/benchmarks/layer1/&lt;case_id&gt;</code> or CI{" "}
          <code>integration-nightly.yml</code>. Browse cases below; open <strong>Кейсы</strong> for{" "}
          <code>graph_expectations</code> preview.
        </Alert>
      ) : null}

      {error && (
        <Typography sx={{ color: "rgba(239, 68, 68, 0.9)", mb: 1 }} role="alert">
          {error}
        </Typography>
      )}

      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          <CursorPrimaryButton
            disabled={isGraphCatalog || selectedCaseIds.length === 0}
            onClick={() => startRun({ caseSelector: selectedCaseIds, label: "selected_cases" })}
          >
            Запустить выделенные ({selectedCaseIds.length})
          </CursorPrimaryButton>
          <CursorButton
            disabled={isGraphCatalog}
            onClick={() => startRun({ caseSelector: "merge_safe", label: "merge_safe" })}
          >
            Запустить merge_safe
          </CursorButton>
          <CursorButton disabled={isGraphCatalog} onClick={() => startRun({ caseSelector: "all", label: "all_cases" })}>
            Запустить все
          </CursorButton>
          <CursorButton
            disabled={isGraphCatalog}
            onClick={() => startRun({ caseSelector: nightlyTierParam, label: nightlyLabel })}
          >
            Запустить {nightlyLabel}
          </CursorButton>
        </Box>
      </Box>

      <Divider sx={{ mb: 2 }} />

      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2 }}>
        <Box>
          <Typography sx={{ fontWeight: 600, mb: 1 }}>merge_safe</Typography>
          <Typography sx={{ color: "rgba(255,255,255,0.6)", mb: 1 }}>
            {loadingCases ? "loading..." : `${mergeSafeCases.length} кейсов`}
          </Typography>
          <FormGroup>
            {mergeSafeCases.map((c) => (
              <FormControlLabel
                key={c.case_id}
                control={
                  <Checkbox
                    checked={selectedSet.has(c.case_id)}
                    onChange={() => setSelectedCaseIds((prev) => _toggleCase(prev, c.case_id))}
                    size="small"
                  />
                }
                label={c.case_id}
              />
            ))}
          </FormGroup>
        </Box>

        <Box>
          <Typography sx={{ fontWeight: 600, mb: 1 }}>{nightlyLabel}</Typography>
          <Typography sx={{ color: "rgba(255,255,255,0.6)", mb: 1 }}>
            {loadingCases ? "loading..." : `${nightlyCases.length} кейсов`}
          </Typography>
          <FormGroup>
            {nightlyCases.map((c) => (
              <FormControlLabel
                key={c.case_id}
                control={
                  <Checkbox
                    checked={selectedSet.has(c.case_id)}
                    onChange={() => setSelectedCaseIds((prev) => _toggleCase(prev, c.case_id))}
                    size="small"
                  />
                }
                label={c.case_id}
              />
            ))}
          </FormGroup>
        </Box>
      </Box>

      <Divider sx={{ my: 2 }} />

      <Typography sx={{ fontWeight: 600, mb: 1 }}>Текущий run</Typography>
      {!runId ? (
        <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>Запустите бенчмарк, чтобы увидеть прогресс.</Typography>
      ) : (
        <Box>
          <Typography sx={{ color: "rgba(255,255,255,0.6)", mb: 1 }}>
            run_id: <span style={{ color: "rgba(255,255,255,0.9)" }}>{runId}</span>
          </Typography>

          <LinearProgress variant="determinate" value={progressPercent} />
          <Typography sx={{ color: "rgba(255,255,255,0.6)", mt: 1 }}>
            {progressCompleted}/{progressTotal} ({progressPercent.toFixed(1)}%)
          </Typography>

          {run && (
            <Box sx={{ mt: 1, display: "flex", gap: 2, flexWrap: "wrap" }}>
              <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>status: {run.status}</Typography>
              {(run.benchmark_family || "layer1") === "layer2" ? (
                <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>
                  avg layer2 recall ratio: {(summary.avg_layer2_recall_ratio ?? 0).toFixed(3)}
                </Typography>
              ) : (
                <>
                  <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>
                    avg names_f1: {(summary.avg_names_f1 ?? 0).toFixed(3)}
                  </Typography>
                  <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>
                    avg sample_arxiv_f1: {(summary.avg_sample_arxiv_f1 ?? 0).toFixed(3)}
                  </Typography>
                </>
              )}
            </Box>
          )}

          <Box sx={{ mt: 2 }}>
            <CursorButton
              disabled={!run || !TERMINAL_STATUSES.includes(run.status)}
              onClick={() => onSwitchToResults?.()}
            >
              Открыть результаты
            </CursorButton>
          </Box>
        </Box>
      )}
    </Box>
  );
}
