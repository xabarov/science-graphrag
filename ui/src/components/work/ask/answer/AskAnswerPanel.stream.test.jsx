/** @vitest-environment jsdom */
import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { normalizeQueryResponse } from "../../../../services/researchApi.js";
import { AskAnswerPanel } from "./AskAnswerPanel.jsx";
import { renderAskAnswer } from "./AskAnswerPanel.testRender.jsx";

describe("AskAnswerPanel — stream chrome", () => {
  it("hides specialist rail for short orphan-only stream", () => {
    const normalized = normalizeQueryResponse({
      answer: "A",
      citations: [],
      graph_context: {},
      retrieval_trace: {},
    });
    renderAskAnswer(
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
      />,
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
    renderAskAnswer(
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
      />,
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
    renderAskAnswer(
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
      />,
    );
    expect(screen.queryByText("chat.run.specialistCompactSummary")).toBeNull();
    expect(screen.queryByText("chat.run.specialistRunsTitle")).toBeNull();
  });

  it("hides answer section title in simple mode when run is finished", async () => {
    const normalized = normalizeQueryResponse({
      answer: "## Title\n\nBody text",
      citations: [],
      graph_context: {},
      retrieval_trace: {},
    });
    renderAskAnswer(
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
      />,
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
    renderAskAnswer(
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
      />,
    );
    expect(screen.queryByText("chat.run.answerSectionTitle")).toBeNull();
    expect(screen.queryByTestId("ask-answer-markdown")).toBeNull();
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
    renderAskAnswer(
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
      />,
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
    renderAskAnswer(
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
      />,
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
    renderAskAnswer(
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
      />,
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
    renderAskAnswer(
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
      />,
    );
    expect(screen.queryByText("chat.sessionMemory.title")).toBeNull();
    expect(screen.queryByText(/Q: prior/)).toBeNull();
    expect(screen.queryByRole("button", { name: "chat.run.inspectToggleShowAria" })).toBeNull();
  });
});
