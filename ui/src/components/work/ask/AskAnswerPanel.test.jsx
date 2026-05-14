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

  it("hides post-run specialist rail in simple mode when turn is finished", () => {
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
    expect(screen.queryByText("chat.run.specialistCompactSummary")).toBeNull();
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

  it("hides answer section title in simple mode when run is finished", async () => {
    const normalized = normalizeQueryResponse({
      answer: "## Title\n\nBody text",
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
            isRunActive={false}
            chatDetailLevel="simple"
          />
        </ThemeProvider>
      </MemoryRouter>,
    );
    expect(screen.queryByText("chat.run.answerSectionTitle")).toBeNull();
    expect(await screen.findByTestId("ask-answer-markdown")).toBeTruthy();
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
            chatDetailLevel="detailed"
          />
        </ThemeProvider>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("post-run-stream-summary").textContent).toContain("Searching works");
  });

  it("hides post-run headline in simple mode after run completes", () => {
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
            chatDetailLevel="simple"
          />
        </ThemeProvider>
      </MemoryRouter>,
    );
    expect(screen.queryByTestId("post-run-stream-summary")).toBeNull();
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
            chatDetailLevel="detailed"
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
    expect(screen.getByText(longBody)).toBeTruthy();
    expect(screen.getByRole("button", { name: "askPanel.citation.expandHide" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "askPanel.citation.expandHide" }));
    expect(screen.getByRole("button", { name: "askPanel.citation.expandShow" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "askPanel.citation.expandShow" }));
    expect(screen.getByRole("button", { name: "askPanel.citation.expandHide" })).toBeTruthy();
    expect(screen.getByText(longBody)).toBeTruthy();
  });

  it("shows partial bulk alert when only some citations omit passage text", async () => {
    const normalized = normalizeQueryResponse({
      answer: "ok",
      citations: [
        { work_id: "w-a", chunk_fingerprint: "fp-a", excerpt: "Has text" },
        { work_id: "w-b", chunk_fingerprint: "fp-b" },
      ],
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
    expect(screen.getByText("askPanel.citation.noSnippetBulkPartial")).toBeTruthy();
    expect(screen.queryByText("askPanel.citation.noSnippet")).toBeNull();
    expect(await screen.findByText(/Has text/)).toBeTruthy();
  });

  it("shows bulk no-snippet alert when citation omits passage fields", () => {
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
    expect(screen.getByText("askPanel.citation.noSnippetBulkAll")).toBeTruthy();
    expect(screen.queryByText("askPanel.citation.noSnippet")).toBeNull();
  });

  it("labels inventory citations as found papers without missing-passage alert", () => {
    const normalized = normalizeQueryResponse({
      answer: "5 papers found",
      citations: [{ work_id: "w-yolo", title: "YOLO paper" }],
      graph_context: {},
      retrieval_trace: {},
      answer_class: "inventory",
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
    expect(screen.getByText("askPanel.citations.inventoryTitle")).toBeTruthy();
    expect(screen.queryByText("askPanel.citations.title")).toBeNull();
    expect(screen.queryByText("askPanel.citation.noSnippetBulkAll")).toBeNull();
    expect(screen.queryByText("askPanel.citation.noSnippet")).toBeNull();
  });

  it("hides chunk id line in simple mode when citation has chunk_fingerprint", () => {
    const normalized = normalizeQueryResponse({
      answer: "ok",
      citations: [{ work_id: "w1", chunk_fingerprint: "fp-abc", excerpt: "Short excerpt" }],
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
            chatDetailLevel="simple"
          />
        </ThemeProvider>
      </MemoryRouter>,
    );
    expect(screen.queryByTestId("citation-chunk-fingerprint-0")).toBeNull();
    expect(screen.getByText(/Short excerpt/)).toBeTruthy();
  });

  it("hides chunk id line in detailed mode when chunk_fingerprint is missing", () => {
    const normalized = normalizeQueryResponse({
      answer: "ok",
      citations: [{ work_id: "w1", excerpt: "Short excerpt", title: "Paper" }],
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
            chatDetailLevel="detailed"
          />
        </ThemeProvider>
      </MemoryRouter>,
    );
    expect(screen.queryByTestId("citation-chunk-fingerprint-0")).toBeNull();
    expect(screen.getByText(/Short excerpt/)).toBeTruthy();
  });

  it("shows chunk id line in detailed mode when citation has chunk_fingerprint", () => {
    const normalized = normalizeQueryResponse({
      answer: "ok",
      citations: [{ work_id: "w1", chunk_fingerprint: "fp-abc", excerpt: "Short excerpt" }],
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
            chatDetailLevel="detailed"
          />
        </ThemeProvider>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("citation-chunk-fingerprint-0").textContent).toMatch(/fp-abc/);
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
    // Identity translator falls through to humanizeUnknownCode in formatAgentWarning.
    const warningAlert = alerts.find((el) => el.textContent?.includes("No workspace"));
    expect(warningAlert).toBeTruthy();
  });

  it("surfaces recursion-limit partial salvage warnings in the alert list", () => {
    const partialMsg = "RECURSION_PARTIAL_UI_COPY";
    const followMsg = "RECURSION_PARTIAL_FOLLOW_COPY";
    const t = (k) => {
      if (k === "chat.warnings.agent_partial_graph_recursion_limit") return partialMsg;
      if (k === "chat.warnings.partial_after_recursion_limit") return followMsg;
      return k;
    };
    const normalized = normalizeQueryResponse({
      answer: "partial answer body",
      citations: [],
      graph_context: {},
      retrieval_trace: {},
      warnings: ["agent_partial_graph_recursion_limit", "partial_after_recursion_limit"],
    });
    render(
      <MemoryRouter>
        <ThemeProvider theme={theme}>
          <AskAnswerPanel
            t={t}
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
    expect(screen.getByText(partialMsg)).toBeTruthy();
    expect(screen.getByText(followMsg)).toBeTruthy();
  });
});
