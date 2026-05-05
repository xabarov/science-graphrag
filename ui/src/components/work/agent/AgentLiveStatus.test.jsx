/** @vitest-environment jsdom */
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import React from "react";
import { ThemeProvider } from "@mui/material/styles";

import { buildAppTheme } from "../../../theme/buildAppTheme.js";
import { AgentLiveStatus } from "./AgentLiveStatus.jsx";

const theme = buildAppTheme("dark");

function renderWithTheme(ui) {
  return render(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

afterEach(() => {
  cleanup();
});

function t(key, vars = {}) {
  let out =
    {
      "chat.run.liveRunCardTitle": "Progress",
      "chat.run.liveStripTitle": "Live",
      "chat.stream.thinking": "Thinking…",
      "chat.stream.intent": "Intent:{{cls}} ({{src}})",
      "chat.stream.intentNoSource": "Intent:{{cls}}",
      "chat.stream.route": "Route:{{fr}} → {{to}}",
      "chat.run.liveExplainShow": "Explain",
      "chat.run.liveExplainHide": "Hide explain",
      "chat.run.liveExplainExpandAria": "Expand explain",
      "chat.run.liveExplainCollapseAria": "Collapse explain",
      "chat.run.decision.label": "Decision",
      "chat.run.decision.why": "Why",
      "chat.run.decision.row": "{{label}}: {{value}}",
      "chat.stream.subagentStarted": "S+{{id}}",
      "chat.run.liveExplainRegionTitle": "Explain region",
      "chat.run.liveExplain.subagentSummary": "Specialist {{id}}: {{summary}}",
      "chat.run.liveStatusShowRecent": "Recent lines",
      "chat.run.liveStatusHideRecent": "Hide lines",
      "chat.run.liveStatusExpandAria": "Expand recent",
      "chat.run.liveStatusCollapseAria": "Collapse recent",
      "chat.run.liveStatusRecentTitle": "Recent",
      "chat.run.answerClass.inventory": "Inventory list",
      "chat.run.intentSource.heuristic": "Heuristic",
      "chat.run.specialist.supervisor": "Coordinator",
      "chat.run.specialist.retrieval_agent": "Corpus search",
      "chat.run.routeReason.semantic_fast_route": "fast semantic route",
    }[key] || key;
  Object.entries(vars).forEach(([k, v]) => {
    out = out.split(`{{${k}}}`).join(String(v));
  });
  return out;
}

describe("AgentLiveStatus", () => {
  it("shows shimmer when active and no meaningful events yet", () => {
    renderWithTheme(<AgentLiveStatus t={t} streamEvents={[]} isActive />);
    expect(screen.getByText("Thinking…")).toBeTruthy();
    expect(screen.getByText("Progress")).toBeTruthy();
  });

  it("shows last meaningful stream line when inactive", () => {
    renderWithTheme(
      <AgentLiveStatus
        t={t}
        streamEvents={[{ type: "intent_classified", answer_class: "inventory", source: "h" }]}
        isActive={false}
      />,
    );
    expect(screen.getByText("Intent:Inventory list (H)")).toBeTruthy();
  });

  it("exposes expandable recent lines with aria when detailed and multiple events", () => {
    renderWithTheme(
      <AgentLiveStatus
        t={t}
        streamEvents={[
          { type: "intent_classified", answer_class: "inventory", source: "h" },
          { type: "specialist_selected", from: "supervisor", to: "retrieval_agent", budget_left: 3 },
        ]}
        isActive={false}
        chatDetailLevel="detailed"
      />,
    );
    const toggle = screen.getByRole("button", { name: "Expand recent" });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText("Route:Coordinator → Corpus search")).toBeTruthy();
    const region = screen.getByRole("region", { name: "Recent" });
    expect(within(region).getByText("Intent:Inventory list (H)")).toBeTruthy();
    expect(within(region).queryByText("Route:Coordinator → Corpus search")).toBeNull();
  });

  it("auto-expands how-the-agent-works in detailed mode when intent and explanations exist", async () => {
    renderWithTheme(
      <AgentLiveStatus
        t={t}
        streamEvents={[
          { type: "intent_classified", answer_class: "inventory", source: "h", reason: "semantic_fast_route" },
          { type: "subagent_started", subagent_id: "retrieval_agent", summary: "semantic_fast_route" },
        ]}
        isActive
        chatDetailLevel="detailed"
      />,
    );
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Collapse explain" })).toBeTruthy();
    });
    expect(screen.getByRole("region", { name: "Explain region" })).toBeTruthy();
  });

  it("omits progress caption, decision block, and tool chips when embedded", () => {
    renderWithTheme(
      <AgentLiveStatus
        t={t}
        streamEvents={[
          { type: "intent_classified", answer_class: "inventory", source: "h", reason: "semantic_fast_route" },
          { type: "tool_call", tool: "idea_search", args_summary: {} },
        ]}
        isActive
        embedded
      />,
    );
    expect(screen.queryByText("Progress")).toBeNull();
    expect(screen.queryByRole("group", { name: "Decision" })).toBeNull();
    expect(screen.queryByText("Literature search")).toBeNull();
  });

  it("hides recent and reasoning toggles in simple mode (default)", () => {
    renderWithTheme(
      <AgentLiveStatus
        t={t}
        streamEvents={[
          { type: "intent_classified", answer_class: "inventory", source: "h", reason: "semantic_fast_route" },
          { type: "specialist_selected", from: "supervisor", to: "retrieval_agent", budget_left: 3 },
        ]}
        isActive={false}
      />,
    );
    expect(screen.queryByRole("button", { name: "Expand recent" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Expand explain" })).toBeNull();
  });

  it("renders without crashing when prefers-reduced-motion is enabled", () => {
    const original = window.matchMedia;
    window.matchMedia = () => ({
      matches: true,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
    });
    try {
      renderWithTheme(
        <AgentLiveStatus
          t={t}
          streamEvents={[{ type: "intent_classified", answer_class: "inventory", source: "h" }]}
          isActive
          chatDetailLevel="detailed"
        />,
      );
      // headline is rendered (active + headline path uses ShimmerLabel which itself respects reduced motion).
      expect(screen.getAllByText(/Inventory/).length).toBeGreaterThan(0);
    } finally {
      window.matchMedia = original;
    }
  });
});
