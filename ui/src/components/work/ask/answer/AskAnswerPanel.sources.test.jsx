/** @vitest-environment jsdom */
import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { normalizeQueryResponse } from "../../../../services/researchApi.js";
import { AskAnswerPanel } from "./AskAnswerPanel.jsx";
import { renderAskAnswer } from "./AskAnswerPanel.testRender.jsx";

describe("AskAnswerPanel — sources / citations", () => {
  it("hides citations block while run is active and there are no citations yet", () => {
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
        streamEvents={[]}
        isRunActive
      />,
    );
    expect(screen.queryByText("askPanel.citations.title")).toBeNull();
  });
  it("hides structured citations block for quote_extraction", () => {
    const normalized = normalizeQueryResponse({
      answer: "Quoted in body",
      citations: [{ work_id: "work-1", chunk_fingerprint: "fp" }],
      graph_context: {},
      retrieval_trace: {},
      answer_class: "quote_extraction",
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
    expect(screen.queryByText("askPanel.citations.title")).toBeNull();
  });
  it("expands a long citation passage in the panel", () => {
    const longBody = "Z".repeat(320);
    const normalized = normalizeQueryResponse({
      answer: "ok",
      citations: [
        { work_id: "work-long", excerpt: longBody, chunk_fingerprint: "fp-z" },
      ],
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
      />,
    );
    expect(screen.getByText(longBody)).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "askPanel.citation.expandHide" }),
    ).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: "askPanel.citation.expandHide" }),
    );
    expect(
      screen.getByRole("button", { name: "askPanel.citation.expandShow" }),
    ).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: "askPanel.citation.expandShow" }),
    );
    expect(
      screen.getByRole("button", { name: "askPanel.citation.expandHide" }),
    ).toBeTruthy();
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
    expect(
      screen.getByText("askPanel.citation.noSnippetBulkPartial"),
    ).toBeTruthy();
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
    expect(screen.getByText("askPanel.citations.inventoryTitle")).toBeTruthy();
    expect(screen.queryByText("askPanel.citations.title")).toBeNull();
    expect(screen.queryByText("askPanel.citation.noSnippetBulkAll")).toBeNull();
    expect(screen.queryByText("askPanel.citation.noSnippet")).toBeNull();
  });
  it("hydrates paper title from inventory for found-papers headline", () => {
    const t = (k, vars = {}) => {
      if (k === "askPanel.citations.inventoryTitle") return "Найденные статьи";
      if (k === "askPanel.citation.workRankLabel")
        return `Статья #${vars.rank}`;
      if (k === "askPanel.citation.sourceLine") return `Источник: ${vars.title}`;
      return k;
    };
    const normalized = normalizeQueryResponse({
      answer: "5 papers",
      citations: [{ work_id: "79a35e97-aaaa-bbbb-cccc-ddddeeee1111" }],
      graph_context: {},
      retrieval_trace: {},
      answer_class: "inventory",
      inventory: {
        papers: [
          {
            work_id: "79a35e97-aaaa-bbbb-cccc-ddddeeee1111",
            title: "DN-DETR: Accelerate DETR Training",
          },
        ],
      },
    });
    renderAskAnswer(
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
      />,
    );
    expect(screen.getByText("Найденные статьи")).toBeTruthy();
    expect(screen.getByText("Статья #1")).toBeTruthy();
    expect(screen.getByText("Источник: DN-DETR: Accelerate DETR Training")).toBeTruthy();
  });
  it("treats work-only citations as found papers even without inventory answer class", () => {
    const t = (k, vars = {}) => {
      if (k === "askPanel.citations.inventoryTitle") return "Найденные статьи";
      if (k === "askPanel.citations.title") return "Цитаты";
      if (k === "askPanel.citation.workRankLabel")
        return `Статья #${vars.rank}`;
      if (k === "askPanel.citation.rankLabel") return `Цитата #${vars.rank}`;
      return k;
    };
    const normalized = normalizeQueryResponse({
      answer: "В вашем хранилище 5 статей.",
      citations: [{ work_id: "793e57...", title: "" }],
      graph_context: {},
      retrieval_trace: {},
      answer_class: "grounded_explanation",
    });
    renderAskAnswer(
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
      />,
    );
    expect(screen.getByText("Найденные статьи")).toBeTruthy();
    expect(screen.queryByText("Цитаты")).toBeNull();
    expect(screen.getByText(/Статья #1/)).toBeTruthy();
    expect(screen.queryByText(/Цитата #1/)).toBeNull();
    expect(screen.queryByText("askPanel.citation.noSnippetBulkAll")).toBeNull();
    expect(screen.queryByText("askPanel.citation.noSnippet")).toBeNull();
  });
  it("hides chunk id line in simple mode when citation has chunk_fingerprint", () => {
    const normalized = normalizeQueryResponse({
      answer: "ok",
      citations: [
        {
          work_id: "w1",
          chunk_fingerprint: "fp-abc",
          excerpt: "Short excerpt",
        },
      ],
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
        chatDetailLevel="detailed"
      />,
    );
    expect(screen.queryByTestId("citation-chunk-fingerprint-0")).toBeNull();
    expect(screen.getByText(/Short excerpt/)).toBeTruthy();
  });
  it("shows chunk id line in detailed mode when citation has chunk_fingerprint", () => {
    const normalized = normalizeQueryResponse({
      answer: "ok",
      citations: [
        {
          work_id: "w1",
          chunk_fingerprint: "fp-abc",
          excerpt: "Short excerpt",
        },
      ],
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
        chatDetailLevel="detailed"
      />,
    );
    expect(
      screen.getByTestId("citation-chunk-fingerprint-0").textContent,
    ).toMatch(/fp-abc/);
  });
});
