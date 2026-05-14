/** @vitest-environment jsdom */
import React from "react";
import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import { ThemeProvider } from "@mui/material/styles";

import { buildAppTheme } from "../../../../theme/buildAppTheme.js";
import { AskSourceList } from "./AskSourceList.jsx";

const appTheme = buildAppTheme("dark");

function renderWithTheme(node) {
  return render(
    <MemoryRouter>
      <ThemeProvider theme={appTheme}>{node}</ThemeProvider>
    </MemoryRouter>,
  );
}

const testMessages = {
  "askPanel.citations.title": "Citations",
  "askPanel.citations.inventoryTitle": "Found papers",
  "askPanel.citations.none": "No citations",
  "askPanel.citation.noSnippetBulkAll": "No passages in all citations",
  "askPanel.citation.noSnippetBulkPartial": "No passages in some citations",
  "askPanel.citation.rankLabel": "Citation #{{rank}}",
  "askPanel.citation.workRankLabel": "Paper #{{rank}}",
  "askPanel.citation.workIdLine": "work_id: {{id}}",
  "askPanel.citation.noSnippet": "No snippet",
  "askPanel.citation.passageLabel": "Passage",
  "askPanel.citation.expandShow": "Show",
  "askPanel.citation.expandHide": "Hide",
  "askPanel.citation.copy": "Copy",
  "askPanel.citation.copied": "Copied",
  "askPanel.citation.tooltipArticle": "Open article",
  "askPanel.citation.tooltipGraphWork": "Open work graph",
  "askPanel.citation.linkReader": "Reader",
  "askPanel.citation.linkGraph": "Graph",
  "askPanel.citation.noWork": "No work",
  "askPanel.chunkLabel": "chunk",
};

function t(key, vars) {
  let value = testMessages[key] ?? key;
  if (vars && typeof vars === "object") {
    for (const [name, raw] of Object.entries(vars)) {
      value = value.replaceAll(`{{${name}}}`, String(raw));
    }
  }
  return value;
}

describe("AskSourceList", () => {
  it("shows inventory label for work-only list", () => {
    renderWithTheme(
      <AskSourceList
        t={t}
        citations={[{ work_id: "w-1", title: "Paper One" }]}
        answerClass="inventory"
        workspaceId="ws-1"
        isRunActive={false}
        hideStructuredCitations={false}
        chatDetailLevel="simple"
      />,
    );
    expect(screen.getByText("Found papers")).toBeTruthy();
    expect(screen.queryByText("Citations")).toBeNull();
  });

  it("suppresses no-snippet alert for full work-only list", () => {
    renderWithTheme(
      <AskSourceList
        t={t}
        citations={[
          { work_id: "w-1", title: "Paper One" },
          { work_id: "w-2", title: "Paper Two" },
        ]}
        answerClass="inventory"
        workspaceId="ws-1"
        isRunActive={false}
        hideStructuredCitations={false}
        chatDetailLevel="simple"
      />,
    );
    expect(screen.queryByText("No passages in all citations")).toBeNull();
  });

  it("shows secondary work_id line in detailed mode for work-only item", () => {
    renderWithTheme(
      <AskSourceList
        t={t}
        citations={[{ work_id: "w-det", title: "Detailed Work" }]}
        answerClass="inventory"
        workspaceId="ws-1"
        isRunActive={false}
        hideStructuredCitations={false}
        chatDetailLevel="detailed"
      />,
    );
    expect(screen.getByText("work_id: w-det")).toBeTruthy();
  });
});
