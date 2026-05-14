/** @vitest-environment jsdom */
import React from "react";
import { describe, expect, it, afterEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { ThemeProvider } from "@mui/material/styles";

import { buildAppTheme } from "../../../../theme/buildAppTheme.js";
import AskResearchPlanPanel from "./AskResearchPlanPanel.jsx";

const appTheme = buildAppTheme("dark");

afterEach(() => {
  cleanup();
});

function renderWithTheme(node) {
  return render(<ThemeProvider theme={appTheme}>{node}</ThemeProvider>);
}

function t(key) {
  const map = {
    "askPanel.researchPlan.title": "Research plan",
    "askPanel.researchPlan.empty": "Empty",
    "askPanel.researchPlan.updating": "Updating",
  };
  return map[key] ?? key;
}

describe("AskResearchPlanPanel", () => {
  it("renders outline plan as ordered list without checkboxes", () => {
    renderWithTheme(
      <AskResearchPlanPanel
        t={t}
        streamHint={null}
        plan={{
          ui_mode: "outline",
          items: [
            { id: "a", content: "First step text", status: "pending" },
            { id: "b", content: "Second step text", status: "pending" },
          ],
        }}
      />,
    );
    expect(screen.queryByRole("checkbox")).toBeNull();
    expect(screen.getByText("First step text")).toBeTruthy();
    expect(screen.getByText("Second step text")).toBeTruthy();
    const ol = document.querySelector("ol");
    expect(ol).toBeTruthy();
  });

  it("uses concise seed scope copy for outline panel", () => {
    renderWithTheme(
      <AskResearchPlanPanel
        t={t}
        streamHint={null}
        plan={{
          ui_mode: "outline",
          items: [{ id: "01_scope", content: "Уточнить цель запроса и критерии ответа.", status: "pending" }],
        }}
      />,
    );
    expect(screen.getByText("Уточнить цель запроса и критерии ответа.")).toBeTruthy();
    expect(screen.queryByRole("checkbox")).toBeNull();
  });

  it("renders checklist mode with disabled checkboxes", () => {
    renderWithTheme(
      <AskResearchPlanPanel
        t={t}
        streamHint={null}
        plan={{
          ui_mode: "checklist",
          items: [
            { id: "a", content: "Todo one", status: "completed" },
            { id: "b", content: "Todo two", status: "pending" },
          ],
        }}
      />,
    );
    const boxes = screen.getAllByRole("checkbox");
    expect(boxes.length).toBe(2);
    expect(screen.getByText("completed")).toBeTruthy();
  });

  it("treats legacy plan without ui_mode but non-pending status as checklist", () => {
    renderWithTheme(
      <AskResearchPlanPanel
        t={t}
        streamHint={null}
        plan={{
          items: [{ id: "a", content: "Active step", status: "in_progress" }],
        }}
      />,
    );
    expect(screen.getAllByRole("checkbox").length).toBe(1);
  });
});
