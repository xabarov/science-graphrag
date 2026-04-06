import React, { useState } from "react";
import Box from "@mui/material/Box";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";

import RunTab from "./RunTab.jsx";
import ResultsTab from "./ResultsTab.jsx";
import CasesTab from "./CasesTab.jsx";

export default function BenchmarkPage() {
  const [tabIdx, setTabIdx] = useState(0);

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
          <Tab label="Результаты" />
          <Tab label="Кейсы" />
        </Tabs>
      </Box>

      {tabIdx === 0 && <RunTab onSwitchToResults={() => setTabIdx(1)} />}
      {tabIdx === 1 && <ResultsTab />}
      {tabIdx === 2 && <CasesTab />}
    </Box>
  );
}

