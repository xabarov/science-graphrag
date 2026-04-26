/** @vitest-environment jsdom */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { normalizeQueryResponse } from "../../services/researchApi.js";
import { AskAnswerPanel } from "./AskAnswerPanel.jsx";

const theme = createTheme();

describe("AskAnswerPanel", () => {
  it("renders normalized warnings", () => {
    const normalized = normalizeQueryResponse({
      answer: "ok",
      citations: [],
      graph_context: {},
      retrieval_trace: {},
      warnings: ["no_workspace"],
    });
    render(
      <MemoryRouter>
        <ThemeProvider theme={theme}>
          <AskAnswerPanel
            t={(k) => k}
            normalized={normalized}
            locked={false}
            inWorkspace={false}
            workId=""
            workspaceWorkId={null}
            retrievalMode="agent"
            agentToolTrace={[]}
            retrievalJsonOpen={false}
            onToggleRetrievalJson={() => {}}
            streamEvents={[]}
            isRunActive={false}
          />
        </ThemeProvider>
      </MemoryRouter>,
    );
    expect(screen.getByRole("alert").textContent).toContain("no_workspace");
  });
});
