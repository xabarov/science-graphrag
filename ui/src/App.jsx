import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import BenchmarkPage from "./pages/BenchmarkPage/BenchmarkPage.jsx";
import DashboardLayout from "./components/layout/DashboardLayout/DashboardLayout.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/benchmark" replace />} />

      <Route element={<DashboardLayout />}>
        <Route path="/benchmark" element={<BenchmarkPage />} />
      </Route>

      <Route path="*" element={<div style={{ padding: 16 }}>Not found</div>} />
    </Routes>
  );
}

