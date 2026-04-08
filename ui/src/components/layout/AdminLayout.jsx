import React, { useMemo } from "react";
import Box from "@mui/material/Box";
import { Link, Outlet, useLocation } from "react-router-dom";

import PageHeader from "./PageHeader.jsx";
import { CursorSmallButton } from "../common/index.js";
import { isAdminModeEnabled } from "./adminVisibility.js";

const ADMIN_HEADER_CONFIG = {
  "/admin": {
    eyebrow: "Operations surface",
    title: "Admin",
    description: "Operational tools stay grouped in a dedicated area so the core research flow remains focused and easier to navigate.",
  },
  "/admin/benchmarks": {
    eyebrow: "Admin tools",
    title: "Benchmarks",
    description: "Run benchmark flows, inspect workbench output, compare runs, and review benchmark cases from the canonical admin route.",
  },
  "/admin/settings": {
    eyebrow: "Admin tools",
    title: "Settings",
    description: "Manage runtime and provider configuration in a dedicated admin surface without mixing it into the main research flow.",
  },
  "/admin/diagnostics": {
    eyebrow: "Admin tools",
    title: "Diagnostics",
    description: "Reserved for operational state and runtime diagnostics, with clear return paths back to the admin hub and home.",
  },
};

export default function AdminLayout() {
  const location = useLocation();
  const header = useMemo(() => ADMIN_HEADER_CONFIG[location.pathname] || ADMIN_HEADER_CONFIG["/admin"], [location.pathname]);
  const showAdminHubAction = location.pathname !== "/admin";
  const adminModeEnabled = isAdminModeEnabled();

  return (
    <Box sx={{ p: 2 }}>
      <PageHeader
        eyebrow={header.eyebrow}
        title={header.title}
        description={header.description}
        actions={
          <>
            {showAdminHubAction ? (
              <CursorSmallButton component={Link} to="/admin" sx={{ textDecoration: "none" }}>
                Admin hub
              </CursorSmallButton>
            ) : null}
            {adminModeEnabled ? (
              <CursorSmallButton component={Link} to="/admin/benchmarks" sx={{ textDecoration: "none" }}>
                Benchmarks
              </CursorSmallButton>
            ) : null}
            <CursorSmallButton component={Link} to="/" sx={{ textDecoration: "none" }}>
              Home
            </CursorSmallButton>
          </>
        }
      />
      <Outlet />
    </Box>
  );
}
