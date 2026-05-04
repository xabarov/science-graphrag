import React from "react";
import { renderToString } from "react-dom/server";
import { ThemeProvider } from "@mui/material/styles";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "../../../i18n/I18nContext.jsx";
import { buildAppTheme } from "../../../theme/buildAppTheme.js";
import { defaultGraphVisibility } from "../model/graphVisibilityFilter.js";
import { graphVisibilityLocalStorageKey } from "./hooks/useGraphWorkspaceData.js";
import WorkspaceGraphToolbar from "./WorkspaceGraphToolbar.jsx";

const ssrTheme = buildAppTheme("dark");

function withProviders(node) {
  return (
    <ThemeProvider theme={ssrTheme}>
      <I18nProvider>{node}</I18nProvider>
    </ThemeProvider>
  );
}

const defaultVisibility = defaultGraphVisibility();

describe("graphVisibilityLocalStorageKey", () => {
  it("uses v1 workspace key", () => {
    expect(graphVisibilityLocalStorageKey("ws-abc", "")).toBe("workspaceGraphVisibility:v1:ws-abc");
  });
  it("uses v1 standalone work key when workspace empty", () => {
    expect(graphVisibilityLocalStorageKey("", "w-1")).toBe("graphWorkVisibility:v1:w-1");
  });
  it("prefers workspace id when both set", () => {
    expect(graphVisibilityLocalStorageKey("ws-x", "w-1")).toBe("workspaceGraphVisibility:v1:ws-x");
  });
  it("trims workspace id", () => {
    expect(graphVisibilityLocalStorageKey("  x  ", "")).toBe("workspaceGraphVisibility:v1:x");
  });
});

describe("WorkspaceGraphToolbar render (SSR smoke)", () => {
  it("renders Nodes menu, view chips, and stats (en workspace)", () => {
    const html = renderToString(
      withProviders(
        <WorkspaceGraphToolbar
          workspaceId="ws-1"
          stats={{ works_count: 3, authors_count: 10, external_citations: 34 }}
          visibility={defaultVisibility}
          onVisibilityChange={() => {}}
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
    expect(html).toContain("All papers in workspace");
    expect(html).toContain("Nodes ·");
    expect(html).not.toContain("Scope:");
    expect(html).not.toContain("Depth");
    expect(html).toContain("Inspector");
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
          visibility={defaultVisibility}
          onVisibilityChange={() => {}}
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
          visibility={defaultVisibility}
          onVisibilityChange={() => {}}
          canvasMode={false}
          labMode={false}
        />,
      ),
    );
    expect(html).toContain("Inspector");
    expect(html).not.toContain("Workspace graph");
  });

  it("renders Nodes menu for standalone work graph when contextWorkId set", () => {
    const html = renderToString(
      withProviders(
        <WorkspaceGraphToolbar
          workspaceId=""
          contextWorkId="w-uuid-1"
          stats={null}
          visibility={{ ...defaultVisibility, types: [...defaultVisibility.types, "Claim"] }}
          onVisibilityChange={() => {}}
          canvasMode={false}
          labMode={false}
        />,
      ),
    );
    expect(html).toContain("Nodes ·");
    expect(html).not.toContain("Workspace graph");
  });
});
