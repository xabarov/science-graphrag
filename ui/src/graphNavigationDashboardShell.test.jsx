/**
 * @vitest-environment jsdom
 *
 * Phase 4 — shell smoke: real [`DashboardLayout`](./components/layout/DashboardLayout/DashboardLayout.jsx)
 * + [`Drawer`](./components/layout/DashboardLayout/Drawer.jsx) after graph-style `setSearchParams` updates.
 * See docs/analysis/graph-navigation-hash-router-remediation-plan-2026-04-28.md §6 Phase 4.
 */
import React from "react";
import { ThemeProvider } from "@mui/material/styles";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HashRouter, Route, Routes, useLocation, useSearchParams } from "react-router-dom";

import { I18nProvider } from "./i18n/I18nContext.jsx";
import { buildAppTheme } from "./theme/buildAppTheme.js";
import DashboardLayout from "./components/layout/DashboardLayout/DashboardLayout.jsx";
import { ADMIN_MODE_STORAGE_KEY } from "./components/layout/adminVisibility.js";
import { SHELL_NAVIGATION_INTENT_EVENT } from "./components/layout/shellNavigationEvents.js";
import { mergeTraceabilityParams } from "./routing/index.js";

const DRAWER_EXPANDED_KEY = "sidebarExpanded";

vi.mock("./utils/workspaceStore.js", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    getWorkspace: vi.fn().mockResolvedValue({ id: "ws-stub", name: "Stub", work_ids: ["w1"] }),
    listWorkspaces: vi.fn().mockResolvedValue([]),
  };
});

const theme = buildAppTheme("dark");

function PathnameEcho() {
  const { pathname } = useLocation();
  return <span data-testid="pathname-echo">{pathname}</span>;
}

function GraphSelectionStub() {
  const [, setSearchParams] = useSearchParams();
  return (
    <div>
      <PathnameEcho />
      <p>graph-stub</p>
      <button
        type="button"
        data-testid="apply-graph-selection"
        onClick={() =>
          setSearchParams(
            (prev) => mergeTraceabilityParams(prev, { nodeId: "n1", edgeId: "" }, { includeTab: false }),
            { replace: true },
          )
        }
      >
        apply-selection
      </button>
    </div>
  );
}

function ChatStub() {
  return (
    <div>
      <PathnameEcho />
      <p>chat-stub</p>
    </div>
  );
}

function ShellApp() {
  return (
    <ThemeProvider theme={theme}>
      <I18nProvider>
        <HashRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            <Route element={<DashboardLayout />}>
              <Route path="/graph" element={<GraphSelectionStub />} />
              <Route path="/chat" element={<ChatStub />} />
            </Route>
          </Routes>
        </HashRouter>
      </I18nProvider>
    </ThemeProvider>
  );
}

describe("graph navigation — DashboardLayout shell (Phase 4)", () => {
  beforeEach(() => {
    try {
      window.localStorage.setItem(ADMIN_MODE_STORAGE_KEY, "false");
      window.localStorage.setItem(DRAWER_EXPANDED_KEY, "true");
    } catch {
      /* ignore */
    }
    window.history.replaceState(null, "", `${window.location.origin}${window.location.pathname}#/graph?work_id=w1`);
  });

  afterEach(() => {
    cleanup();
    try {
      window.localStorage.removeItem(ADMIN_MODE_STORAGE_KEY);
    } catch {
      /* ignore */
    }
    window.history.replaceState(null, "", `${window.location.origin}${window.location.pathname}`);
  });

  it("drawer navigates from /graph to /chat after selection updates via setSearchParams", async () => {
    render(<ShellApp />);
    const shellNavigationIntent = vi.fn();
    window.addEventListener(SHELL_NAVIGATION_INTENT_EVENT, shellNavigationIntent);

    await waitFor(() => {
      expect(screen.getByTestId("pathname-echo").textContent).toBe("/graph");
    });
    expect(screen.getByText("graph-stub")).toBeTruthy();

    fireEvent.click(screen.getByTestId("apply-graph-selection"));
    expect(window.location.hash).toContain("node=n1");
    expect(window.location.hash).toContain("work_id=w1");

    const chatLink = screen.getByRole("link", { name: /chat/i });
    fireEvent.pointerDown(chatLink);
    expect(shellNavigationIntent).toHaveBeenCalledWith(expect.objectContaining({ type: SHELL_NAVIGATION_INTENT_EVENT }));
    fireEvent.click(chatLink);

    await waitFor(() => {
      expect(screen.getByText("chat-stub")).toBeTruthy();
    });
    const echoes = screen.getAllByTestId("pathname-echo");
    expect(echoes.some((el) => el.textContent === "/chat")).toBe(true);
    expect(window.location.hash.startsWith("#/chat")).toBe(true);
    window.removeEventListener(SHELL_NAVIGATION_INTENT_EVENT, shellNavigationIntent);
  });

  /**
   * Selection updates use `replace: true` (same history entry as /graph). Navigating to /chat pushes
   * a new entry; back returns to /graph with the last replaced query (selection preserved).
   */
  it("browser back returns to /graph with selection query after drawer navigation to /chat", async () => {
    render(<ShellApp />);

    await waitFor(() => {
      expect(screen.getByTestId("pathname-echo").textContent).toBe("/graph");
    });

    fireEvent.click(screen.getByTestId("apply-graph-selection"));
    fireEvent.click(screen.getByRole("link", { name: /chat/i }));

    await waitFor(() => {
      expect(screen.getByText("chat-stub")).toBeTruthy();
    });

    window.history.back();

    await waitFor(() => {
      expect(screen.getByText("graph-stub")).toBeTruthy();
    });
    expect(window.location.hash).toContain("/graph");
    expect(window.location.hash).toContain("node=n1");
  });
});
