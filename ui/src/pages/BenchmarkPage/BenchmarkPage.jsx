import React, { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import { Link, useLocation, useSearchParams } from "react-router-dom";

import { CursorSmallButton } from "../../components/common/index.js";

import BenchmarkWorkbenchTab from "./BenchmarkWorkbenchTab.jsx";
import CompareTab from "./CompareTab.jsx";
import RunTab from "./RunTab.jsx";
import ResultsTab from "./ResultsTab.jsx";
import CasesTab from "./CasesTab.jsx";

const TAB_BY_NAME = { launch: 0, workbench: 1, results: 2, compare: 3, cases: 4 };

export default function BenchmarkPage() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [tabIdx, setTabIdx] = useState(0);
  const [selectedRunId, setSelectedRunId] = useState(() => window.localStorage.getItem("benchmark:lastRunId") || null);
  const [selectedCaseId, setSelectedCaseId] = useState(null);
  const canonicalAdminPath = useMemo(() => {
    const query = searchParams.toString();
    return `/admin/benchmarks${query ? `?${query}` : ""}`;
  }, [searchParams]);
  const showAdminReturn = location.pathname !== "/admin/benchmarks";

  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect -- sync shell from /benchmark? query (external nav) */
    const t = searchParams.get("tab");
    const run = searchParams.get("run");
    const c = searchParams.get("case");
    if (t != null && t !== "") {
      const n = Number(t);
      if (!Number.isNaN(n) && n >= 0 && n <= 4) {
        setTabIdx(n);
      } else if (TAB_BY_NAME[t] != null) {
        setTabIdx(TAB_BY_NAME[t]);
      }
    }
    if (run) {
      setSelectedRunId(run);
      window.localStorage.setItem("benchmark:lastRunId", run);
    }
    if (c) setSelectedCaseId(c);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [searchParams]);

  function openWorkbench(runId, caseId = null) {
    if (runId) {
      setSelectedRunId(runId);
      window.localStorage.setItem("benchmark:lastRunId", runId);
    }
    setSelectedCaseId(caseId);
    setTabIdx(1);
  }

  return (
    <Box>
      <Box sx={{ px: 2, pt: 0.5, pb: 1.5, display: "flex", flexWrap: "wrap", gap: 1 }}>
        <CursorSmallButton component={Link} to="/admin" sx={{ textDecoration: "none" }}>
          Admin hub
        </CursorSmallButton>
        <CursorSmallButton component={Link} to="/" sx={{ textDecoration: "none" }}>
          Home
        </CursorSmallButton>
        {showAdminReturn ? (
          <CursorSmallButton component={Link} to={canonicalAdminPath} sx={{ textDecoration: "none" }}>
            Reopen canonical route
          </CursorSmallButton>
        ) : null}
      </Box>
      <Box sx={{ padding: 2, borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
        <Tabs
          value={tabIdx}
          onChange={(e, v) => setTabIdx(v)}
          textColor="inherit"
          indicatorColor="secondary"
          variant="scrollable"
        >
          <Tab label="Запуск" />
          <Tab label="Workbench" />
          <Tab label="Результаты" />
          <Tab label="Сравнение" />
          <Tab label="Кейсы" />
        </Tabs>
      </Box>

      {tabIdx === 0 && <RunTab onSwitchToResults={() => setTabIdx(2)} />}
      {tabIdx === 1 && (
        <BenchmarkWorkbenchTab
          selectedRunId={selectedRunId}
          selectedCaseId={selectedCaseId}
          onSelectRun={setSelectedRunId}
          onSelectCase={setSelectedCaseId}
        />
      )}
      {tabIdx === 2 && <ResultsTab onOpenWorkbench={openWorkbench} />}
      {tabIdx === 3 && <CompareTab onOpenWorkbench={openWorkbench} />}
      {tabIdx === 4 && <CasesTab />}
    </Box>
  );
}

