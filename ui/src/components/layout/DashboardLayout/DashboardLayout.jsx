import React from "react";
import Box from "@mui/material/Box";
import { Outlet } from "react-router-dom";

import { WorkspaceContextProvider } from "../WorkspaceContext.jsx";
import WorkspaceContextChip from "../WorkspaceContextChip.jsx";
import Drawer from "./Drawer.jsx";

export default function DashboardLayout() {
  return (
    <WorkspaceContextProvider>
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
              display: "flex",
              alignItems: "center",
              justifyContent: "flex-end",
              gap: 1,
              px: { xs: 1.5, sm: 2 },
              py: 1,
              borderBottom: "1px solid rgba(255,255,255,0.06)",
              minHeight: 48,
            }}
          >
            <WorkspaceContextChip />
          </Box>
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
    </WorkspaceContextProvider>
  );
}

