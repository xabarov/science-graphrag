import React from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Box from "@mui/material/Box";

import HomePage from "./pages/HomePage.jsx";
import AdminEntryPage from "./pages/AdminEntryPage.jsx";
import BenchmarkPage from "./pages/BenchmarkPage/BenchmarkPage.jsx";
import CorpusPage from "./pages/CorpusPage.jsx";
import WorkspacePage from "./pages/WorkspacePage/WorkspacePage.jsx";
import ReaderPage from "./pages/ReaderPage.jsx";
import GraphPage from "./pages/GraphPage.jsx";
import AskPage from "./pages/AskPage.jsx";
import EvidencePage from "./pages/EvidencePage.jsx";
import SettingsPage from "./pages/SettingsPage.jsx";
import DiagnosticsPage from "./pages/DiagnosticsPage.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";
import PageHeader from "./components/layout/PageHeader.jsx";
import DashboardLayout from "./components/layout/DashboardLayout/DashboardLayout.jsx";
import AdminVisibilityGate from "./components/layout/AdminVisibilityGate.jsx";
import AdminLayout from "./components/layout/AdminLayout.jsx";
import { isAdminModeEnabled } from "./components/layout/adminVisibility.js";
import { buildLegacyAdminRedirectTarget } from "./routeCompatibility.js";

function LegacyAdminRedirect({ to }) {
  const location = useLocation();
  return <Navigate to={buildLegacyAdminRedirectTarget(to, location.search) || to} replace />;
}

function AdminRouteShell() {
  if (isAdminModeEnabled()) {
    return <AdminLayout />;
  }
  return (
    <Box sx={{ p: 2, maxWidth: 960 }}>
      <PageHeader
        eyebrow="Research surface"
        title="Admin tools are hidden"
        description="This app is currently running in research-only mode, so operational routes stay out of the primary shell."
      />
      <AdminVisibilityGate />
    </Box>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/home" element={<Navigate to="/" replace />} />
        <Route path="/corpus" element={<CorpusPage />} />
        <Route path="/workspace" element={<WorkspacePage />} />
        <Route path="/reader" element={<ReaderPage />} />
        <Route path="/graph" element={<GraphPage />} />
        <Route path="/ask" element={<AskPage />} />
        <Route path="/evidence" element={<EvidencePage />} />
        <Route path="/admin" element={<AdminRouteShell />}>
          <Route index element={<AdminEntryPage />} />
          <Route path="benchmarks" element={<BenchmarkPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="diagnostics" element={<DiagnosticsPage />} />
        </Route>
        <Route path="/benchmark" element={<LegacyAdminRedirect to="/benchmark" />} />
        <Route path="/settings" element={<LegacyAdminRedirect to="/settings" />} />
        <Route path="/diagnostics" element={<LegacyAdminRedirect to="/diagnostics" />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
