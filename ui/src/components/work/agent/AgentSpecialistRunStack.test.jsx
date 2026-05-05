/** @vitest-environment jsdom */
import { ThemeProvider } from "@mui/material/styles";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { buildAppTheme } from "../../../theme/buildAppTheme.js";
import { AgentSpecialistRunStack } from "./AgentSpecialistRunStack.jsx";

const theme = buildAppTheme("dark");

function t(key, vars = {}) {
  let out =
    {
      "chat.run.specialistRunsTitle": "Specialist runs",
      "chat.run.specialistOrphanLabel": "Preamble · {{count}} events",
      "chat.run.specialistRunLabel": "{{from}} → {{to}} · {{count}} events",
      "chat.run.specialistExpandAria": "Expand specialist run details",
      "chat.run.specialistCollapseAria": "Collapse specialist run details",
      "chat.run.specialistExpand": "Show",
      "chat.run.specialistCollapse": "Hide",
      "chat.stream.intent": "Intent:{{cls}}:{{src}}",
      "chat.stream.intentNoSource": "Intent:{{cls}}",
      "chat.run.answerClass.inventory": "Inventory list",
      "chat.run.intentSource.heuristic": "Heuristic",
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
    const expandButtons = screen.getAllByRole("button", { name: "Expand specialist run details" });
    fireEvent.click(expandButtons[0]);
    await waitFor(() => {
      expect(screen.getByText("Intent:Inventory list:Heuristic")).toBeTruthy();
    });
  });
});
