/** @vitest-environment jsdom */
/**
 * Integration-style checks for safe "reasoning" UX: explanations from coordinator fields,
 * not raw tool args. Complements backend SSE tests in tests/test_api_agent_v2_stream_parity.py.
 */
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import React from "react";
import { ThemeProvider } from "@mui/material/styles";

import { buildAppTheme } from "../../../theme/buildAppTheme.js";
import { AgentLiveStatus } from "./AgentLiveStatus.jsx";

const theme = buildAppTheme("dark");

function t(key, vars = {}) {
  const table = {
    "chat.run.liveRunCardTitle": "Progress",
    "chat.stream.thinking": "Thinking…",
    "chat.run.productStep.searching_literature": "Searching works…",
    "chat.run.productStep.exploring_graph": "Exploring graph…",
    "chat.run.liveExplainShow": "How it works",
    "chat.run.liveExplainHide": "Hide",
    "chat.run.liveExplainExpandAria": "Expand reasoning",
    "chat.run.liveExplainCollapseAria": "Collapse reasoning",
    "chat.run.liveExplainRegionTitle": "Reasoning",
    "chat.run.liveExplain.intentReason": "Intent {{cls}}: {{reason}}",
    "chat.run.liveExplain.routeReason": "Route: {{reason}}",
    "chat.run.liveExplain.subagentSummary": "Agent {{id}}: {{summary}}",
    "chat.run.liveStatusShowRecent": "Recent",
    "chat.run.liveStatusHideRecent": "Hide recent",
    "chat.run.liveStatusExpandAria": "Expand recent",
    "chat.run.liveStatusCollapseAria": "Collapse recent",
    "chat.run.liveStatusRecentTitle": "Recent status",
    "chat.run.toolLabel.idea_search": "Literature search",
    "chat.run.toolLabel.cypher_query": "Graph query",
    "chat.run.live.toolCall": "{{tool}}",
    "chat.run.live.toolCallQuery": "{{tool}} · {{q}}",
    "chat.run.decision.label": "Decision",
    "chat.run.decision.why": "Why",
    "chat.run.decision.row": "{{label}}: {{value}}",
    "chat.run.answerClass.inventory": "Inventory listing",
  };
  let out = table[key] || key;
  Object.entries(vars).forEach(([k, v]) => {
    out = out.split(`{{${k}}}`).join(String(v));
  });
  return out;
}

function renderWithTheme(ui) {
  return render(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

afterEach(() => cleanup());

describe("AgentLiveStatus reasoning (integration)", () => {
  it("surfaces decision and why from intent / specialist reason above the headline", () => {
    renderWithTheme(
      <AgentLiveStatus
        t={t}
        isActive
        streamEvents={[
          {
            type: "intent_classified",
            answer_class: "inventory",
            source: "shortcut",
            reason: "Classified as catalog-style question.",
          },
          {
            type: "specialist_selected",
            from: "supervisor",
            to: "retrieval_agent",
            budget_left: 7,
            reason: "Route to retrieval for grounded evidence.",
          },
          { type: "product_step", code: "searching_literature", tool: "idea_search" },
        ]}
      />,
    );

    expect(screen.getByText("Searching works…")).toBeTruthy();

    const decisionGroup = screen.getByRole("group", { name: "Decision" });
    expect(within(decisionGroup).getByText("Decision: Inventory listing")).toBeTruthy();
    expect(within(decisionGroup).getByText(/Why: Classified as catalog-style question\./)).toBeTruthy();
  });

  it("shows tool activity chips from tool_call stream while active", () => {
    renderWithTheme(
      <AgentLiveStatus
        t={t}
        isActive
        streamEvents={[
          { type: "product_step", code: "exploring_graph", tool: "cypher_query" },
          { type: "tool_call", step: 1, tool: "idea_search", args_summary: {} },
          { type: "tool_call", step: 2, tool: "cypher_query", args_summary: {} },
        ]}
      />,
    );

    expect(screen.getByText("Exploring graph…")).toBeTruthy();
    expect(screen.getByText("Literature search")).toBeTruthy();
    expect(screen.getByText("Graph query")).toBeTruthy();
  });
});
