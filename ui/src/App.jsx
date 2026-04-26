import React, { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";

import HomePage from "./pages/HomePage.jsx";
import AdminEntryPage from "./pages/AdminEntryPage.jsx";
import WorkspacesPage from "./pages/WorkspacesPage.jsx";
import ReaderPage from "./pages/ReaderPage.jsx";
import ChatPage from "./pages/ChatPage.jsx";
import LegacyAskRedirect from "./pages/LegacyAskRedirect.jsx";
import EvidencePage from "./pages/EvidencePage.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";

const WorkspacePage = lazy(() => import("./pages/WorkspacePage/WorkspacePage.jsx"));
const BenchmarkPage = lazy(() => import("./pages/BenchmarkPage/BenchmarkPage.jsx"));
const SettingsPage = lazy(() => import("./pages/SettingsPage.jsx"));
const DiagnosticsPage = lazy(() => import("./pages/DiagnosticsPage.jsx"));
const GraphPage = lazy(() => import("./pages/GraphPage.jsx"));
import { useI18n } from "./i18n/useI18n.js";
import PageHeader from "./components/layout/PageHeader.jsx";
import DashboardLayout from "./components/layout/DashboardLayout/DashboardLayout.jsx";
import AdminVisibilityGate from "./components/layout/AdminVisibilityGate.jsx";
import AdminLayout from "./components/layout/AdminLayout.jsx";
import { mainShellContentSx } from "./components/layout/mainShellContentSx.js";
import { isAdminModeEnabled } from "./components/layout/adminVisibility.js";
import { buildLegacyAdminRedirectTarget } from "./routeCompatibility.js";

function LegacyAdminRedirect({ to }) {
  const location = useLocation();
  return <Navigate to={buildLegacyAdminRedirectTarget(to, location.search) || to} replace />;
}

function AdminRouteShell() {
  const { t } = useI18n();
  if (isAdminModeEnabled()) {
    return <AdminLayout />;
  }
  return (
    <Box sx={{ p: 2, ...mainShellContentSx }}>
      <PageHeader
        eyebrow={t("app.adminHidden.eyebrow")}
        title={t("app.adminHidden.title")}
        description={t("app.adminHidden.description")}
      />
      <AdminVisibilityGate />
    </Box>
  );
}

function LazyRouteFallback() {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "40vh" }}>
      <CircularProgress size={28} sx={{ color: "rgba(129,140,248,0.85)" }} />
    </Box>
  );
}

export default function App() {
  return (
    <Box sx={{ flex: 1, minHeight: 0, height: "100%", display: "flex", flexDirection: "column" }}>
      <Routes>
      <Route element={<DashboardLayout />}>
        <Route path="/" element={<Navigate to="/workspaces" replace />} />
        <Route path="/home" element={<HomePage />} />
        <Route path="/workspaces" element={<WorkspacesPage />} />
        <Route path="/corpus" element={<Navigate to="/workspaces" replace />} />
        <Route
          path="/workspace"
          element={
            <Suspense fallback={<LazyRouteFallback />}>
              <WorkspacePage />
            </Suspense>
          }
        />
        <Route path="/reader" element={<ReaderPage />} />
        <Route
          path="/graph"
          element={
            <Suspense fallback={<LazyRouteFallback />}>
              <GraphPage />
            </Suspense>
          }
        />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/ask" element={<LegacyAskRedirect />} />
        <Route path="/evidence" element={<EvidencePage />} />
        <Route path="/admin" element={<AdminRouteShell />}>
          <Route index element={<AdminEntryPage />} />
          <Route
            path="benchmarks"
            element={
              <Suspense fallback={<LazyRouteFallback />}>
                <BenchmarkPage />
              </Suspense>
            }
          />
          <Route
            path="settings"
            element={
              <Suspense fallback={<LazyRouteFallback />}>
                <SettingsPage />
              </Suspense>
            }
          />
          <Route
            path="diagnostics"
            element={
              <Suspense fallback={<LazyRouteFallback />}>
                <DiagnosticsPage />
              </Suspense>
            }
          />
        </Route>
        <Route path="/benchmark" element={<LegacyAdminRedirect to="/benchmark" />} />
        <Route path="/settings" element={<LegacyAdminRedirect to="/settings" />} />
        <Route path="/diagnostics" element={<LegacyAdminRedirect to="/diagnostics" />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
      </Routes>
    </Box>
  );
}
