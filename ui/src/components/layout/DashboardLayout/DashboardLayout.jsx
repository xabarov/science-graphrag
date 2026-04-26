import React from "react";
import Box from "@mui/material/Box";
import { Outlet } from "react-router-dom";

import { WorkspaceContextProvider } from "../WorkspaceContext.jsx";
import WorkspaceContextChip from "../WorkspaceContextChip.jsx";
import Drawer from "./Drawer.jsx";

export default function DashboardLayout() {
  return (
    <WorkspaceContextProvider>
      <Box sx={{ display: "flex", flex: 1, minHeight: 0, width: "100%", overflow: "hidden" }}>
        <Drawer />
        <Box
          component="main"
          sx={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            minWidth: 0,
            minHeight: 0,
            overflow: "hidden",
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
              flexShrink: 0,
            }}
          >
            <WorkspaceContextChip />
          </Box>
          <Box
            sx={{
              flex: 1,
              minHeight: 0,
              minWidth: 0,
              overflow: "auto",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <Outlet />
          </Box>
        </Box>
      </Box>
    </WorkspaceContextProvider>
  );
}

