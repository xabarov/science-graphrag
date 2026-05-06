/** @vitest-environment jsdom */
import { ThemeProvider } from "@mui/material/styles";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { buildAppTheme } from "../../../theme/buildAppTheme.js";
import { AgentSpecialistRunStack } from "./AgentSpecialistRunStack.jsx";

const theme = buildAppTheme("dark");

afterEach(() => {
  cleanup();
});

function t(key, vars = {}) {
  let out =
    {
      "chat.run.specialistRunsTitle": "Specialist runs",
      "chat.run.specialistOrphanLabel": "Preamble · {{count}} events",
      "chat.run.specialistRunLabel": "{{from}} → {{to}} · {{count}} events",
      "chat.run.specialistExpandAria": "Expand processing trace",
      "chat.run.specialistCollapseAria": "Collapse processing trace",
      "chat.run.specialistExpand": "Show",
      "chat.run.specialistCollapse": "Hide",
      "chat.stream.intent": "Intent:{{cls}}:{{src}}",
      "chat.stream.intentNoSource": "Intent:{{cls}}",
      "chat.stream.route": "R:{{fr}}:{{to}}",
      "chat.run.answerClass.inventory": "Inventory list",
      "chat.run.intentSource.heuristic": "Heuristic",
      "chat.run.live.toolCall": "{{tool}}",
      "chat.run.toolLabel.generic": "Tool: {{tool}}",
      "chat.run.headline.repeatedSuffix": "{{base}} (×{{count}})",
      "chat.run.live.toolCallRepeated": "{{base}} (×{{count}})",
      "chat.run.live.productStepRepeated": "{{base}} (×{{count}})",
      "chat.run.specialistShowAllCalls": "Show every call",
      "chat.run.specialistHideAllCalls": "Show collapsed calls",
      "chat.stream.toolResultLabel": "Tool result",
      "chat.stream.rowsLabel": "rows",
      "chat.run.productStep.composing_answer": "Composing answer…",
      "chat.stream.answerSynthesisFinished": "Answer ready",
    }[key] || key;
  Object.entries(vars).forEach(([k, v]) => {
    out = out.split(`{{${k}}}`).join(String(v));
  });
  return out;
}

describe("AgentSpecialistRunStack", () => {
  it("expands to show formatted stream lines", async () => {
    render(
      <ThemeProvider theme={theme}>
        <AgentSpecialistRunStack
          t={t}
          streamEvents={[
            { type: "intent_classified", answer_class: "inventory", source: "heuristic" },
            { type: "specialist_selected", from: "sup", to: "ret" },
          ]}
        />
      </ThemeProvider>,
    );
    expect(screen.getByText("Specialist runs")).toBeTruthy();
    const expandButtons = screen.getAllByRole("button", { name: "Expand processing trace" });
    fireEvent.click(expandButtons[0]);
    await waitFor(() => {
      expect(screen.getByText("Intent:Inventory list:Heuristic")).toBeTruthy();
    });
  });

  it("offers expanded call list for repeated tools in detailed mode", async () => {
    render(
      <ThemeProvider theme={theme}>
        <AgentSpecialistRunStack
          t={t}
          chatDetailLevel="detailed"
          streamEvents={[
            { type: "specialist_selected", from: "sup", to: "ret" },
            { type: "tool_call", tool: "idea_search" },
            { type: "tool_call", tool: "idea_search" },
          ]}
        />
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Expand processing trace" }));
    await waitFor(() => {
      expect(screen.getByText(/Tool: idea_search \(×2\)/)).toBeTruthy();
    });
    fireEvent.click(screen.getByRole("button", { name: "Show every call" }));
    await waitFor(() => {
      expect(screen.getAllByText(/Tool: idea_search/).length).toBeGreaterThanOrEqual(2);
    });
  });

  it("hides final_answer tool rows and terminal envelope from the expanded trace", async () => {
    render(
      <ThemeProvider theme={theme}>
        <AgentSpecialistRunStack
          t={t}
          streamEvents={[
            { type: "specialist_selected", from: "sup", to: "ret" },
            { type: "tool_call", tool: "final_answer" },
            { type: "tool_result", tool: "final_answer", row_count: 3 },
            { type: "product_step", code: "composing_answer" },
            { type: "answer_synthesis_finished" },
            { type: "final_answer", answer: "markdown" },
          ]}
        />
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Expand processing trace" }));
    await waitFor(() => {
      expect(screen.queryByText(/final_answer/i)).toBeNull();
      expect(screen.getByText("Composing answer…")).toBeTruthy();
    });
  });

  it("does not surface raw tool_execution lines in the expanded trace", async () => {
    render(
      <ThemeProvider theme={theme}>
        <AgentSpecialistRunStack
          t={t}
          streamEvents={[
            { type: "specialist_selected", from: "sup", to: "ret" },
            { type: "tool_execution", phase: "pre_hooks", ok: true },
            { type: "tool_call", tool: "idea_search" },
            { type: "tool_execution", phase: "post_hooks", ok: true, elapsed_ms: 5 },
            { type: "tool_result", tool: "idea_search", row_count: 1 },
          ]}
        />
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Expand processing trace" }));
    await waitFor(() => {
      expect(screen.queryByText("tool_execution")).toBeNull();
      expect(screen.getByText(/Tool result: Tool: idea_search/)).toBeTruthy();
    });
  });
});
