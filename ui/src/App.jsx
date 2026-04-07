import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import BenchmarkPage from "./pages/BenchmarkPage/BenchmarkPage.jsx";
import CorpusPage from "./pages/CorpusPage.jsx";
import WorkspacePage from "./pages/WorkspacePage/WorkspacePage.jsx";
import ReaderPage from "./pages/ReaderPage.jsx";
import GraphPage from "./pages/GraphPage.jsx";
import AskPage from "./pages/AskPage.jsx";
import EvidencePage from "./pages/EvidencePage.jsx";
import SettingsPage from "./pages/SettingsPage.jsx";
import DiagnosticsPage from "./pages/DiagnosticsPage.jsx";
import DashboardLayout from "./components/layout/DashboardLayout/DashboardLayout.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/corpus" replace />} />

      <Route element={<DashboardLayout />}>
        <Route path="/corpus" element={<CorpusPage />} />
        <Route path="/workspace" element={<WorkspacePage />} />
        <Route path="/reader" element={<ReaderPage />} />
        <Route path="/graph" element={<GraphPage />} />
        <Route path="/ask" element={<AskPage />} />
        <Route path="/evidence" element={<EvidencePage />} />
        <Route path="/benchmark" element={<BenchmarkPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/diagnostics" element={<DiagnosticsPage />} />
      </Route>

      <Route path="*" element={<div style={{ padding: 16 }}>Not found</div>} />
    </Routes>
  );
}
