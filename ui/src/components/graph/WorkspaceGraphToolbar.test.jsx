import React from "react";
import { renderToString } from "react-dom/server";
import { ThemeProvider } from "@mui/material/styles";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "../../i18n/I18nContext.jsx";
import { buildAppTheme } from "../../theme/buildAppTheme.js";
import WorkspaceGraphToolbar, { graphToolbarLocalStorageKey } from "./WorkspaceGraphToolbar.jsx";

const ssrTheme = buildAppTheme("dark");

function withProviders(node) {
  return (
    <ThemeProvider theme={ssrTheme}>
      <I18nProvider>{node}</I18nProvider>
    </ThemeProvider>
  );
}

const defaultValue = {
  mode: "inner_only",
  depth: 1,
  includeExternal: false,
  nodeTypesCsv: "Work,Author",
  externalMinInternalCiters: 0,
  includeClaims: false,
};

describe("WorkspaceGraphToolbar storage keys", () => {
  it("matches per-workspace persist contract (Wave J)", () => {
    const wid = "ws-abc";
    expect(graphToolbarLocalStorageKey(wid, "Mode")).toBe("workspaceGraphMode:ws-abc");
    expect(graphToolbarLocalStorageKey(wid, "Depth")).toBe("workspaceGraphDepth:ws-abc");
    expect(graphToolbarLocalStorageKey(wid, "IncludeExternal")).toBe("workspaceGraphIncludeExternal:ws-abc");
    expect(graphToolbarLocalStorageKey(wid, "NodeTypes")).toBe("workspaceGraphNodeTypes:ws-abc");
    expect(graphToolbarLocalStorageKey(wid, "IncludeClaims")).toBe("workspaceGraphIncludeClaims:ws-abc");
  });

  it("trims workspace id", () => {
    expect(graphToolbarLocalStorageKey("  x  ", "Mode")).toBe("workspaceGraphMode:x");
  });
});

describe("WorkspaceGraphToolbar render (SSR smoke)", () => {
  it("renders workspace filters, depth 1°, nodes summary, and view chips (en)", () => {
    const html = renderToString(
      withProviders(
        <WorkspaceGraphToolbar
          workspaceId="ws-1"
          stats={{ works_count: 3, authors_count: 10, external_citations: 34 }}
          value={defaultValue}
          onChange={() => {}}
          canvasMode
          localFindQuery=""
          onLocalFindChange={() => {}}
          onLocalFindClear={() => {}}
          onFocusFirstMatch={() => {}}
          localFindFocusDisabled
          detailsVisible
          legendOpen
          diagnosticsOpen={false}
          onToggleDetails={() => {}}
          onToggleLegend={() => {}}
          onToggleDiagnostics={() => {}}
          labMode={false}
        />,
      ),
    );
    expect(html).toContain("Workspace graph");
    expect(html).toContain("Scope:");
    expect(html).toContain("Inner");
    expect(html).toContain("1°");
    expect(html).toContain("Nodes: 2/6");
    expect(html).toContain("Details");
    expect(html).toContain("Legend");
    expect(html).toContain("Diagnostics");
    expect(html).toContain("3 works");
  });

  it("omits diagnostics chip when labMode", () => {
    const html = renderToString(
      withProviders(
        <WorkspaceGraphToolbar
          workspaceId="ws-1"
          stats={null}
          value={defaultValue}
          onChange={() => {}}
          canvasMode={false}
          labMode
        />,
      ),
    );
    expect(html).not.toContain("Diagnostics");
  });

  it("renders view chips without workspace row when workspaceId empty and canvas off", () => {
    const html = renderToString(
      withProviders(
        <WorkspaceGraphToolbar
          workspaceId=""
          stats={null}
          value={defaultValue}
          onChange={() => {}}
          canvasMode={false}
          labMode={false}
        />,
      ),
    );
    expect(html).toContain("Details");
    expect(html).not.toContain("Workspace graph");
  });

  it("shows claims toggle for standalone work graph when contextWorkId set", () => {
    const html = renderToString(
      withProviders(
        <WorkspaceGraphToolbar
          workspaceId=""
          contextWorkId="w-uuid-1"
          stats={null}
          value={{ ...defaultValue, includeClaims: true }}
          onChange={() => {}}
          canvasMode={false}
          labMode={false}
        />,
      ),
    );
    expect(html).toContain("Claims");
  });
});
