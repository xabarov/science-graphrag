import { describe, expect, it } from "vitest";

import { buildLegacyAdminRedirectTarget, LEGACY_ADMIN_ROUTE_MAP } from "./routeCompatibility.js";
import { buildWorkspacePath } from "./pages/WorkspacePage/utils/workContext.js";

describe("routeCompatibility", () => {
  it("maps legacy admin routes to canonical admin paths", () => {
    expect(LEGACY_ADMIN_ROUTE_MAP).toEqual({
      "/benchmark": "/admin/benchmarks",
      "/settings": "/admin/settings",
      "/diagnostics": "/admin/diagnostics",
    });
  });

  it("preserves query params when redirecting legacy admin routes", () => {
    expect(buildLegacyAdminRedirectTarget("/benchmark", "?tab=workbench")).toBe("/admin/benchmarks?tab=workbench");
    expect(buildLegacyAdminRedirectTarget("/settings", "")).toBe("/admin/settings");
    expect(buildLegacyAdminRedirectTarget("/diagnostics", "?from=home")).toBe("/admin/diagnostics?from=home");
  });

  it("returns null for non-legacy routes", () => {
    expect(buildLegacyAdminRedirectTarget("/admin")).toBeNull();
    expect(buildLegacyAdminRedirectTarget("/workspace")).toBeNull();
  });

  it("keeps workspace deep links unchanged", () => {
    expect(buildWorkspacePath("paper-1", "graph")).toBe("/workspace?work_id=paper-1&tab=graph");
    expect(buildWorkspacePath("paper-2", "ask")).toBe("/workspace?work_id=paper-2&tab=ask");
  });
});
