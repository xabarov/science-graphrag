import React, { useEffect, useMemo, useState } from "react";
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

import BenchmarkWorkbenchTab from "./BenchmarkWorkbenchTab.jsx";
import CompareTab from "./CompareTab.jsx";
import RunTab from "./RunTab.jsx";
import ResultsTab from "./ResultsTab.jsx";
import CasesTab from "./CasesTab.jsx";
import TrustSignalPanel from "./TrustSignalPanel.jsx";
import { useI18n } from "../../i18n/useI18n.js";

const TAB_BY_NAME = { launch: 0, workbench: 1, results: 2, compare: 3, cases: 4 };

export default function BenchmarkPage() {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
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
    const tabParam = searchParams.get("tab");
    const run = searchParams.get("run");
    const c = searchParams.get("case");
    if (tabParam != null && tabParam !== "") {
      const n = Number(tabParam);
      if (!Number.isNaN(n) && n >= 0 && n <= 4) {
        setTabIdx(n);
      } else if (TAB_BY_NAME[tabParam] != null) {
        setTabIdx(TAB_BY_NAME[tabParam]);
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
      <Box sx={{ px: 2, pb: 1.5 }}>
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
      <TrustSignalPanel />
      <Box sx={{ padding: 2, borderBottom: `1px solid ${tk.border.default}` }}>
        <Tabs
          value={tabIdx}
          onChange={(e, v) => setTabIdx(v)}
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
          <Tab label={t("benchmarkPage.tab.launch")} />
          <Tab label={t("benchmarkPage.tab.workbench")} />
          <Tab label={t("benchmarkPage.tab.results")} />
          <Tab label={t("benchmarkPage.tab.compare")} />
          <Tab label={t("benchmarkPage.tab.cases")} />
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

