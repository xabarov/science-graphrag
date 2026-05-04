/** @vitest-environment jsdom */
import { ThemeProvider } from "@mui/material/styles";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { normalizeQueryResponse } from "../../../services/researchApi.js";
import { buildAppTheme } from "../../../theme/buildAppTheme.js";
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
            chatDetailLevel="detailed"
          />
        </ThemeProvider>
      </MemoryRouter>,
    );
    expect(screen.getByText("chat.run.specialistRunsTitle")).toBeTruthy();
  });

  it("shows compact specialist line in simple mode when specialist_selected is present", () => {
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
            chatDetailLevel="simple"
          />
        </ThemeProvider>
      </MemoryRouter>,
    );
    expect(screen.getByText("chat.run.specialistCompactSummary")).toBeTruthy();
    expect(screen.queryByText("chat.run.specialistRunsTitle")).toBeNull();
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

  it("hides answer section title while run is active with no answer text", () => {
    const normalized = normalizeQueryResponse({
      answer: "",
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
            streamEvents={[{ type: "product_step", code: "searching_literature", tool: "idea_search" }]}
            isRunActive
          />
        </ThemeProvider>
      </MemoryRouter>,
    );
    expect(screen.queryByText("chat.run.answerSectionTitle")).toBeNull();
    expect(screen.queryByTestId("ask-answer-markdown")).toBeNull();
  });

  it("hides citations block while run is active and there are no citations yet", () => {
    const normalized = normalizeQueryResponse({
      answer: "",
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
            streamEvents={[]}
            isRunActive
          />
        </ThemeProvider>
      </MemoryRouter>,
    );
    expect(screen.queryByText("askPanel.citations.title")).toBeNull();
  });

  it("shows post-run headline from last stream event after run completes", () => {
    const t2 = (k, vars = {}) => {
      const m = {
        "chat.run.productStep.searching_literature": "Searching works…",
      };
      let out = m[k] ?? k;
      Object.entries(vars || {}).forEach(([kk, v]) => {
        out = out.split(`{{${kk}}}`).join(String(v));
      });
      return out;
    };
    const normalized = normalizeQueryResponse({
      answer: "Final",
      citations: [],
      graph_context: {},
      retrieval_trace: {},
    });
    render(
      <MemoryRouter>
        <ThemeProvider theme={theme}>
          <AskAnswerPanel
            t={t2}
            normalized={normalized}
            locked={false}
            inWorkspace={false}
            workId=""
            workspaceWorkId={null}
            retrievalMode="agent"
            agentToolTrace={[]}
            retrievalJsonOpen={false}
            onToggleRetrievalJson={() => {}}
            streamEvents={[{ type: "product_step", code: "searching_literature", tool: "idea_search" }]}
            isRunActive={false}
          />
        </ThemeProvider>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("post-run-stream-summary").textContent).toContain("Searching works");
  });

  it("omits post-run summary when the last meaningful stream event is answer_synthesis_finished", () => {
    const normalized = normalizeQueryResponse({
      answer: "Final",
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
            streamEvents={[{ type: "answer_synthesis_finished" }]}
            isRunActive={false}
          />
        </ThemeProvider>
      </MemoryRouter>,
    );
    expect(screen.queryByTestId("post-run-stream-summary")).toBeNull();
  });

  it("does not show server session memory excerpt in the answer panel", () => {
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
    expect(screen.queryByText("chat.sessionMemory.title")).toBeNull();
    expect(screen.queryByText(/Q: prior/)).toBeNull();
    expect(screen.queryByRole("button", { name: "chat.run.inspectToggleShowAria" })).toBeNull();
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
      answer_class: "grounded_explanation",
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

  it("hides structured citations block for quote_extraction", () => {
    const normalized = normalizeQueryResponse({
      answer: "Quoted in body",
      citations: [{ work_id: "work-1", chunk_fingerprint: "fp" }],
      graph_context: {},
      retrieval_trace: {},
      answer_class: "quote_extraction",
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
    expect(screen.queryByText("askPanel.citations.title")).toBeNull();
  });

  it("expands a long citation passage in the panel", () => {
    const longBody = "Z".repeat(320);
    const normalized = normalizeQueryResponse({
      answer: "ok",
      citations: [{ work_id: "work-long", excerpt: longBody, chunk_fingerprint: "fp-z" }],
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
            streamEvents={[]}
            isRunActive={false}
          />
        </ThemeProvider>
      </MemoryRouter>,
    );
    expect(screen.getByRole("button", { name: "askPanel.citation.expandShow" })).toBeTruthy();
    expect(screen.queryByText(longBody)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "askPanel.citation.expandShow" }));
    expect(screen.getByText(longBody)).toBeTruthy();
  });

  it("shows noSnippet when citation omits passage fields", () => {
    const normalized = normalizeQueryResponse({
      answer: "ok",
      citations: [{ work_id: "w-empty", chunk_fingerprint: "fp" }],
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
            streamEvents={[]}
            isRunActive={false}
          />
        </ThemeProvider>
      </MemoryRouter>,
    );
    expect(screen.getByText("askPanel.citation.noSnippet")).toBeTruthy();
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
