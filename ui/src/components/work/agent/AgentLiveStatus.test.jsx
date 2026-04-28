/** @vitest-environment jsdom */
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
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
      "chat.stream.route": "Route:{{fr}} → {{to}}",
      "chat.run.liveExplainShow": "Explain",
      "chat.run.liveExplainHide": "Hide explain",
      "chat.run.liveExplainExpandAria": "Expand explain",
      "chat.run.liveExplainCollapseAria": "Collapse explain",
      "chat.run.liveExplainRegionTitle": "Explain region",
      "chat.run.liveStatusShowRecent": "Recent lines",
      "chat.run.liveStatusHideRecent": "Hide lines",
      "chat.run.liveStatusExpandAria": "Expand recent",
      "chat.run.liveStatusCollapseAria": "Collapse recent",
      "chat.run.liveStatusRecentTitle": "Recent",
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
    expect(screen.getByText("Intent:inventory (h)")).toBeTruthy();
  });

  it("exposes expandable recent lines with aria when multiple events", () => {
    renderWithTheme(
      <AgentLiveStatus
        t={t}
        streamEvents={[
          { type: "intent_classified", answer_class: "inventory", source: "h" },
          { type: "specialist_selected", from: "sup", to: "retrieval", budget_left: 3 },
        ]}
        isActive={false}
      />,
    );
    const toggle = screen.getByRole("button", { name: "Expand recent" });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText("Route:sup → retrieval")).toBeTruthy();
    const region = screen.getByRole("region", { name: "Recent" });
    expect(within(region).getByText("Intent:inventory (h)")).toBeTruthy();
    expect(within(region).queryByText("Route:sup → retrieval")).toBeNull();
  });
});
