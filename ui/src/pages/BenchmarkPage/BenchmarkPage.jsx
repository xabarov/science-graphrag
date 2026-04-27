import React, { useCallback, useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import { Link, useLocation, useSearchParams } from "react-router-dom";

import AdminPanelSettingsOutlinedIcon from "@mui/icons-material/AdminPanelSettingsOutlined";
import HomeOutlinedIcon from "@mui/icons-material/HomeOutlined";
import OpenInNewOutlinedIcon from "@mui/icons-material/OpenInNewOutlined";

import { CursorIconAction } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";

import BenchmarkAnalysisTab from "./BenchmarkAnalysisTab.jsx";
import BenchmarkExperimentsTab from "./BenchmarkExperimentsTab.jsx";
import BenchmarkOverviewTab from "./BenchmarkOverviewTab.jsx";
import CasesTab from "./CasesTab.jsx";
import RunTab from "./RunTab.jsx";

import {
  mergeBenchmarkTabIntoSearchParams,
  mergeRunLabQueryIntoSearchParams,
  normalizeAnalysisView,
  parseBenchmarkTabQuery,
} from "./experimentCatalog.js";

export default function BenchmarkPage() {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [tabIdx, setTabIdx] = useState(0);
  const [analysisView, setAnalysisView] = useState(/** @type {"results"|"compare"|"workbench"} */ ("results"));
  const [selectedRunId, setSelectedRunId] = useState(() => window.localStorage.getItem("benchmark:lastRunId") || null);
  const [selectedCaseId, setSelectedCaseId] = useState(null);
  const canonicalAdminPath = useMemo(() => {
    const query = searchParams.toString();
    return `/admin/benchmarks${query ? `?${query}` : ""}`;
  }, [searchParams]);
  const showAdminReturn = location.pathname !== "/admin/benchmarks";

  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect -- sync shell from URL (external nav / back) */
    const tabParam = searchParams.get("tab");
    const avParam = searchParams.get("analysisView");
    const { tabIndex, analysisView: av } = parseBenchmarkTabQuery(tabParam, avParam);
    setTabIdx(tabIndex);
    setAnalysisView(av);
    // Only overwrite run/case from URL when those keys are present so we do not wipe
    // `lastRunId` rehydration on first paint (`?tab=overview` with no `run` param).
    if (searchParams.has("run")) {
      const run = searchParams.get("run");
      if (run) {
        setSelectedRunId(run);
        window.localStorage.setItem("benchmark:lastRunId", run);
      } else {
        setSelectedRunId(null);
      }
    }
    if (searchParams.has("case")) {
      const c = searchParams.get("case");
      setSelectedCaseId(c || null);
    }
    const runParam = searchParams.get("run");
    const workbenchFixtureFirst =
      tabIndex === 3 && av === "workbench" && Boolean(searchParams.get("case")) && !runParam;
    if (workbenchFixtureFirst) {
      setSelectedRunId(null);
    }
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [searchParams]);

  const onNavigate = useCallback(
    (opts) => {
      const nextIdx = opts.tabIndex;
      let nextAv = /** @type {"results"|"compare"|"workbench"} */ ("results");
      if (nextIdx === 3) {
        nextAv =
          opts.analysisView != null ? normalizeAnalysisView(opts.analysisView) : normalizeAnalysisView(analysisView);
        setAnalysisView(nextAv);
      }
      setTabIdx(nextIdx);
      let merged = mergeBenchmarkTabIntoSearchParams(
        searchParams,
        nextIdx,
        nextIdx === 3 ? nextAv : "results",
      );
      if ("experimentId" in opts || "runMode" in opts || "packId" in opts) {
        merged = mergeRunLabQueryIntoSearchParams(merged, {
          experimentId: "experimentId" in opts ? opts.experimentId : undefined,
          runMode: "runMode" in opts ? opts.runMode : undefined,
          packId: "packId" in opts ? opts.packId : undefined,
        });
      }
      setSearchParams(merged, { replace: true });
    },
    [analysisView, searchParams, setSearchParams],
  );

  const handleOpenAnalysisWithGroup = useCallback(
    (runIds) => {
      if (!runIds?.length) return;
      const first = runIds[0];
      setSelectedRunId(first);
      window.localStorage.setItem("benchmark:lastRunId", first);
      setTabIdx(3);
      setAnalysisView(runIds.length > 1 ? "compare" : "results");
      let merged = mergeBenchmarkTabIntoSearchParams(searchParams, 3, runIds.length > 1 ? "compare" : "results");
      merged.set("run", first);
      if (runIds.length > 1) merged.set("runs", runIds.join(","));
      else merged.delete("runs");
      setSearchParams(merged, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  /**
   * @param {string | null} runId
   * @param {string | null} [caseId]
   * @param {{ caseFamily?: string | null, compareBaselineRunId?: string | null, compareMetric?: string | null }} [opts]
   */
  const openWorkbench = useCallback(
    (runId, caseId = null, opts = {}) => {
      if (runId) {
        setSelectedRunId(runId);
        window.localStorage.setItem("benchmark:lastRunId", runId);
      } else {
        setSelectedRunId(null);
      }
      setSelectedCaseId(caseId);
      setTabIdx(3);
      setAnalysisView("workbench");
      const merged = mergeBenchmarkTabIntoSearchParams(searchParams, 3, "workbench");
      if (runId) merged.set("run", runId);
      else merged.delete("run");
      if (caseId) merged.set("case", caseId);
      else merged.delete("case");

      if (runId) {
        merged.delete("caseFamily");
      } else if (caseId && opts.caseFamily) {
        merged.set("caseFamily", opts.caseFamily);
      } else if (!caseId) {
        merged.delete("caseFamily");
      }

      if (opts.compareBaselineRunId && opts.compareMetric) {
        merged.set("cmpBaseline", opts.compareBaselineRunId);
        merged.set("cmpMetric", encodeURIComponent(String(opts.compareMetric)));
      } else {
        merged.delete("cmpBaseline");
        merged.delete("cmpMetric");
      }
      setSearchParams(merged, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const openCaseFromCatalog = useCallback(
    (catalogCaseId, family) => {
      if (!catalogCaseId) return;
      setSelectedRunId(null);
      setSelectedCaseId(catalogCaseId);
      setTabIdx(3);
      setAnalysisView("workbench");
      const merged = mergeBenchmarkTabIntoSearchParams(searchParams, 3, "workbench");
      merged.delete("run");
      merged.set("case", catalogCaseId);
      merged.set("caseFamily", family || "layer1");
      merged.delete("cmpBaseline");
      merged.delete("cmpMetric");
      setSearchParams(merged, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const setAnalysisViewInUrl = useCallback(
    (view) => {
      const v = normalizeAnalysisView(view);
      setAnalysisView(v);
      const merged = mergeBenchmarkTabIntoSearchParams(searchParams, 3, v);
      setSearchParams(merged, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const handleSelectRun = useCallback(
    (runId) => {
      setSelectedRunId(runId);
      if (runId) window.localStorage.setItem("benchmark:lastRunId", runId);
      const next = new URLSearchParams(searchParams.toString());
      if (runId) next.set("run", runId);
      else next.delete("run");
      next.delete("cmpBaseline");
      next.delete("cmpMetric");
      // Clearing run implies no meaningful case selection in URL or state.
      if (!runId) {
        next.delete("case");
        setSelectedCaseId(null);
      }
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const handleSelectCase = useCallback(
    (caseId) => {
      setSelectedCaseId(caseId);
      const next = new URLSearchParams(searchParams.toString());
      if (caseId) next.set("case", caseId);
      else next.delete("case");
      next.delete("cmpBaseline");
      next.delete("cmpMetric");
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  return (
    <Box>
      <Box sx={{ px: 2, pt: 0.5, pb: 1.5, display: "flex", flexWrap: "wrap", gap: 0.75 }}>
        <CursorIconAction component={Link} to="/admin" title={t("benchmarkPage.adminHub")}>
          <AdminPanelSettingsOutlinedIcon sx={{ fontSize: "1.1rem" }} />
        </CursorIconAction>
        <CursorIconAction component={Link} to="/" title={t("benchmarkPage.home")}>
          <HomeOutlinedIcon sx={{ fontSize: "1.1rem" }} />
        </CursorIconAction>
        {showAdminReturn ? (
          <CursorIconAction component={Link} to={canonicalAdminPath} title={t("benchmarkPage.reopenCanonical")}>
            <OpenInNewOutlinedIcon sx={{ fontSize: "1.1rem" }} />
          </CursorIconAction>
        ) : null}
      </Box>
      <Box sx={{ px: 2, pb: 1 }}>
        <Alert
          severity="info"
          sx={{
            fontSize: "0.8125rem",
            backgroundColor: tk.surface.subtle,
            border: `1px solid ${tk.border.default}`,
            color: tk.text.primary,
            "& .MuiAlert-icon": { color: tk.accent.fg },
          }}
        >
          <Typography component="div" variant="body2" sx={{ fontSize: "0.8125rem", lineHeight: 1.5 }}>
            {t("benchmarkPage.triageAlert")}
          </Typography>
        </Alert>
      </Box>
      <Box sx={{ px: 2, pb: 1 }}>
        <Typography sx={{ fontWeight: 600, fontSize: "0.9375rem", color: tk.text.primary }}>{t("benchmarkPage.pageTitle")}</Typography>
        <Typography sx={{ mt: 0.35, fontSize: "0.8125rem", color: tk.text.secondary, lineHeight: 1.55, maxWidth: 960 }}>
          {t("benchmarkPage.pageSubtitle")}
        </Typography>
      </Box>
      <Box sx={{ padding: 2, borderBottom: `1px solid ${tk.border.default}` }}>
        <Tabs
          value={tabIdx}
          onChange={(e, v) => onNavigate({ tabIndex: v })}
          textColor="inherit"
          indicatorColor="secondary"
          variant="scrollable"
          sx={{
            "& .MuiTab-root:focus-visible": {
              outline: `2px solid ${tk.accent.fg}`,
              outlineOffset: 2,
            },
          }}
        >
          <Tab label={t("benchmarkPage.tab.overview")} />
          <Tab label={t("benchmarkPage.tab.experiments")} />
          <Tab label={t("benchmarkPage.tab.runLab")} />
          <Tab label={t("benchmarkPage.tab.analysis")} />
          <Tab label={t("benchmarkPage.tab.cases")} />
        </Tabs>
      </Box>

      {tabIdx === 0 ? <BenchmarkOverviewTab onNavigate={onNavigate} onOpenWorkbench={openWorkbench} /> : null}
      {tabIdx === 1 ? <BenchmarkExperimentsTab onNavigate={onNavigate} /> : null}
      {tabIdx === 2 ? (
        <RunTab
          onSwitchToResults={() => onNavigate({ tabIndex: 3, analysisView: "results" })}
          onOpenAnalysisWithGroup={handleOpenAnalysisWithGroup}
        />
      ) : null}
      {tabIdx === 3 ? (
        <BenchmarkAnalysisTab
          analysisView={analysisView}
          onAnalysisViewChange={setAnalysisViewInUrl}
          onOpenWorkbench={openWorkbench}
          selectedRunId={selectedRunId}
          selectedCaseId={selectedCaseId}
          onSelectRun={handleSelectRun}
          onSelectCase={handleSelectCase}
          searchParams={searchParams}
        />
      ) : null}
      {tabIdx === 4 ? <CasesTab onOpenCaseInWorkbench={openCaseFromCatalog} /> : null}
    </Box>
  );
}
