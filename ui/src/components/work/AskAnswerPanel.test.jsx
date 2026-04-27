/** @vitest-environment jsdom */
import { ThemeProvider } from "@mui/material/styles";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { normalizeQueryResponse } from "../../services/researchApi.js";
import { buildAppTheme } from "../../theme/buildAppTheme.js";
import { AskAnswerPanel } from "./AskAnswerPanel.jsx";

const theme = buildAppTheme("dark");

afterEach(() => {
  cleanup();
});

describe("AskAnswerPanel", () => {
  it("hides specialist rail for short orphan-only stream", () => {
    const normalized = normalizeQueryResponse({
      answer: "A",
      citations: [],
      graph_context: {},
      retrieval_trace: {},
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
            streamEvents={[{ type: "intent_classified", answer_class: "inventory", source: "h" }]}
            isRunActive={false}
          />
        </ThemeProvider>
      </MemoryRouter>,
    );
    expect(screen.queryByText("chat.run.specialistRunsTitle")).toBeNull();
  });

  it("shows specialist rail when specialist_selected is present", () => {
    const normalized = normalizeQueryResponse({
      answer: "A",
      citations: [],
      graph_context: {},
      retrieval_trace: {},
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
            streamEvents={[
              { type: "intent_classified", answer_class: "inventory", source: "h" },
              { type: "specialist_selected", from: "a", to: "b" },
            ]}
            isRunActive={false}
          />
        </ThemeProvider>
      </MemoryRouter>,
    );
    expect(screen.getByText("chat.run.specialistRunsTitle")).toBeTruthy();
  });

  it("shows degraded info alert when graph_context has degraded", () => {
    const normalized = normalizeQueryResponse({
      answer: "A",
      citations: [],
      graph_context: { degraded: ["x"] },
      retrieval_trace: {},
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
    expect(screen.getByText("askPanel.answer.degraded")).toBeTruthy();
  });

  it("shows server session memory when excerpt present after run", () => {
    const normalized = normalizeQueryResponse({
      answer: "A",
      citations: [],
      graph_context: {},
      retrieval_trace: {},
      session_summary_excerpt: "Q: prior\nA: done",
      thread_id: "t1",
      run_metadata: { compaction: { kinds: ["turn_digest", "rolling_memory"] } },
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
    expect(screen.getByText("chat.sessionMemory.title")).toBeTruthy();
    expect(screen.getByText(/Q: prior/)).toBeTruthy();
    expect(screen.getByText(/turn_digest/)).toBeTruthy();
  });

  it("renders composed final answer with typed blocks and citations", async () => {
    const normalized = normalizeQueryResponse({
      answer: "## Composed title\n\n**Composed** answer body",
      citations: [
        {
          work_id: "work-1",
          rank: 1,
          score: 0.91,
          excerpt: "Unique excerpt for composed test",
          chunk_fingerprint: "fp-z",
        },
      ],
      graph_context: {},
      retrieval_trace: {},
      inventory: { work_count: 2 },
      quote_candidates: [{ text: "Quoted passage", work_id: "work-1" }],
      answer_class: "quote_extraction",
    });
    render(
      <MemoryRouter>
        <ThemeProvider theme={theme}>
          <div data-testid="ask-composed-root">
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
          </div>
        </ThemeProvider>
      </MemoryRouter>,
    );
    const root = within(screen.getByTestId("ask-composed-root"));
    expect(await root.findByRole("heading", { name: "Composed title" })).toBeTruthy();
    expect(root.getByText("Composed")).toBeTruthy();
    expect(root.getByText(/answer body/)).toBeTruthy();
    expect(root.getByText("chat.typed.inventoryTitle")).toBeTruthy();
    expect(root.getByText("chat.typed.quotesTitle")).toBeTruthy();
    expect(root.getByText("askPanel.citations.title")).toBeTruthy();
    expect(root.getByText(/Unique excerpt for composed test/)).toBeTruthy();
  });

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
    const alerts = screen.getAllByRole("alert");
    const warningAlert = alerts.find((el) => el.textContent?.includes("no_workspace"));
    expect(warningAlert).toBeTruthy();
  });
});
