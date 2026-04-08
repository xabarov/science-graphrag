import React from "react";
import Box from "@mui/material/Box";
import { Outlet } from "react-router-dom";

import Drawer from "./Drawer.jsx";

export default function DashboardLayout() {
  return (
    <Box sx={{ display: "flex" }}>
      <Drawer />
      <Box
        component="main"
        sx={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          minHeight: "100vh",
          minWidth: 0,
          backgroundColor: "#0a0a0a",
          borderLeft: "1px solid rgba(255, 255, 255, 0.08)",
        }}
      >
        <Box
          sx={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
            minWidth: 0,
          }}
        >
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}

