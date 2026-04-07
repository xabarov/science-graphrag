import React, { useState } from "react";
import Box from "@mui/material/Box";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";

import BenchmarkWorkbenchTab from "./BenchmarkWorkbenchTab.jsx";
import CompareTab from "./CompareTab.jsx";
import RunTab from "./RunTab.jsx";
import ResultsTab from "./ResultsTab.jsx";
import CasesTab from "./CasesTab.jsx";

export default function BenchmarkPage() {
  const [tabIdx, setTabIdx] = useState(0);
  const [selectedRunId, setSelectedRunId] = useState(() => window.localStorage.getItem("benchmark:lastRunId") || null);
  const [selectedCaseId, setSelectedCaseId] = useState(null);

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

