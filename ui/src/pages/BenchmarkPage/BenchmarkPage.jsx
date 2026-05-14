import React from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import { Link, useLocation } from "react-router-dom";

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
import { useBenchmarkPageRouting } from "./useBenchmarkPageRouting.js";

export default function BenchmarkPage() {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const location = useLocation();
  const {
    searchParams,
    tabIdx,
    analysisView,
    selectedRunId,
    selectedCaseId,
    canonicalAdminPath,
    onNavigate,
    handleOpenAnalysisWithGroup,
    openWorkbench,
    openCaseFromCatalog,
    setAnalysisViewInUrl,
    handleSelectRun,
    handleSelectCase,
  } = useBenchmarkPageRouting();

  const showAdminReturn = location.pathname !== "/admin/benchmarks";

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
