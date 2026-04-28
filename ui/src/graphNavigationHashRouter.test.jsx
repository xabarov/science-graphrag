/**
 * @vitest-environment jsdom
 *
 * Phase 0–1 — graph navigation under HashRouter (see docs/analysis/graph-navigation-hash-router-remediation-plan-2026-04-28.md).
 *
 * ## Manual QA (deterministic checklist when investigating prod-only issues)
 *
 * 1. Run `npm run dev` in `ui/`, open the app with the same URL shape as production (hash routing).
 * 2. Path A — drawer: pick a workspace → open **Graph** from the drawer → select a node or edge on the graph
 *    (any action that updates the URL via selection) → click **Reader**, **Chat**, or **Workspace** in the drawer.
 *    Record: full address bar URL before/after; whether the main content switches; console errors.
 * 3. Path B — paper row: go to `/workspace` → click the graph icon on a paper row (`workGraphUrl`) → change graph selection
 *    → navigate away via the drawer again. Record the same signals.
 *
 * ## Automated guard (variant B)
 *
 * Mirrors production: `HashRouter` + `setSearchParams(mergeTraceabilityParams(..., { replace: true }))` (same contract as
 * `GraphPage`) + `Link` navigation. If this passes in CI but users still see a dead-end, bias investigation toward
 * blocked clicks/overlays, lazy-loaded shell, or base-path differences — not raw hash parsing.
 *
 * **Variant C (Phase 4):** real shell — [`graphNavigationDashboardShell.test.jsx`](./graphNavigationDashboardShell.test.jsx)
 * (`DashboardLayout` + drawer + back-after-chat).
 *
 * ## Phase 0 failure-class note (evidence)
 *
 * The isolated case passes under jsdom: `Link` navigation after updating graph selection via React Router does not
 * break `HashRouter`. Treat production dead-ends as likely **blocked click handling** (canvas/modal/pointer-events),
 * **stale location in a larger shell**, or **history/base-path** issues until disproven — not generic hash query
 * parsing errors (those are covered by `traceabilityState.test.js`).
 */
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { HashRouter, Link, Outlet, Route, Routes, useLocation, useSearchParams } from "react-router-dom";

import { mergeTraceabilityParams } from "./routing/index.js";

/** Keeps route assertions on React Router state, not only on `window.location.hash`. */
function PathnameEcho() {
  const { pathname } = useLocation();
  return <span data-testid="pathname-echo">{pathname}</span>;
}

function ShellLayout() {
  return (
    <div>
      <PathnameEcho />
      <Link data-testid="nav-chat" to="/chat">
        Chat
      </Link>
      <Outlet />
    </div>
  );
}

function GraphSelectionStub() {
  const [, setSearchParams] = useSearchParams();
  return (
    <div>
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
  return <p>chat-stub</p>;
}

function TestApp() {
  return (
    <HashRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route element={<ShellLayout />}>
          <Route path="/graph" element={<GraphSelectionStub />} />
          <Route path="/chat" element={<ChatStub />} />
        </Route>
      </Routes>
    </HashRouter>
  );
}

describe("graph navigation (HashRouter + traceability search params)", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", `${window.location.origin}/#/graph?work_id=w1`);
  });

  afterEach(() => {
    cleanup();
    window.history.replaceState(null, "", `${window.location.origin}/`);
  });

  it("navigates from /graph to another route after updating selection via setSearchParams", async () => {
    render(<TestApp />);

    expect(screen.getByText("graph-stub")).toBeTruthy();
    expect(screen.getByTestId("pathname-echo").textContent).toBe("/graph");

    fireEvent.click(screen.getByTestId("apply-graph-selection"));

    expect(window.location.hash).toContain("node=n1");
    expect(window.location.hash).toContain("work_id=w1");

    fireEvent.click(screen.getByTestId("nav-chat"));

    await waitFor(() => {
      expect(screen.getByTestId("pathname-echo").textContent).toBe("/chat");
    });
    expect(screen.getByText("chat-stub")).toBeTruthy();
    expect(window.location.hash.startsWith("#/chat")).toBe(true);
  });
});
