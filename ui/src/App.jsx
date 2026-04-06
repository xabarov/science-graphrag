import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import BenchmarkPage from "./pages/BenchmarkPage/BenchmarkPage.jsx";
import WorkspacePage from "./pages/WorkspacePage.jsx";
import ReaderPage from "./pages/ReaderPage.jsx";
import GraphPage from "./pages/GraphPage.jsx";
import AskPage from "./pages/AskPage.jsx";
import EvidencePage from "./pages/EvidencePage.jsx";
import DashboardLayout from "./components/layout/DashboardLayout/DashboardLayout.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/workspace" replace />} />

      <Route element={<DashboardLayout />}>
        <Route path="/workspace" element={<WorkspacePage />} />
        <Route path="/reader" element={<ReaderPage />} />
        <Route path="/graph" element={<GraphPage />} />
        <Route path="/ask" element={<AskPage />} />
        <Route path="/evidence" element={<EvidencePage />} />
        <Route path="/benchmark" element={<BenchmarkPage />} />
      </Route>

      <Route path="*" element={<div style={{ padding: 16 }}>Not found</div>} />
    </Routes>
  );
}
