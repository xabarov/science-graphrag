import React from "react";
import Box from "@mui/material/Box";
import { useTheme } from "@mui/material/styles";
import { Outlet } from "react-router-dom";

import { WorkspaceContextProvider } from "../WorkspaceContext.jsx";
import WorkspaceSwitcher from "../WorkspaceSwitcher.jsx";
import Drawer from "./Drawer.jsx";

export default function DashboardLayout() {
  const tk = useTheme().appTokens;
  return (
    <WorkspaceContextProvider>
      <Box sx={{ display: "flex", flex: 1, minHeight: 0, width: "100%" }}>
        <Drawer />
        <Box
          component="main"
          sx={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            minWidth: 0,
            minHeight: 0,
            backgroundColor: tk.surface.app,
            borderLeft: `1px solid ${tk.border.default}`,
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
              borderBottom: `1px solid ${tk.border.default}`,
              minHeight: 48,
              flexShrink: 0,
            }}
          >
            <WorkspaceSwitcher />
          </Box>
          <Box
            sx={{
              flex: 1,
              minHeight: 0,
              minWidth: 0,
              overflowY: "auto",
              overflowX: "hidden",
              display: "flex",
              flexDirection: "column",
              scrollPaddingBottom: "24px",
              pb: { xs: 2, sm: 3 },
            }}
          >
            <Outlet />
          </Box>
        </Box>
      </Box>
    </WorkspaceContextProvider>
  );
}

