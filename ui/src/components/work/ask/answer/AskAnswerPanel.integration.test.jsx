/** @vitest-environment jsdom */
import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { normalizeQueryResponse } from "../../../../services/researchApi.js";
import { AskAnswerPanel } from "./AskAnswerPanel.jsx";
import { renderAskAnswer } from "./AskAnswerPanel.testRender.jsx";

describe("AskAnswerPanel — integration smoke", () => {
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
    renderAskAnswer(
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
      </div>,
    );
    const root = within(screen.getByTestId("ask-composed-root"));
    expect(
      await root.findByRole("heading", { name: "Composed title" }),
    ).toBeTruthy();
    expect(root.getByText("Composed")).toBeTruthy();
    expect(root.getByText(/answer body/)).toBeTruthy();
    expect(root.getByText("chat.typed.inventoryTitle")).toBeTruthy();
    expect(root.getByText("chat.typed.quotesTitle")).toBeTruthy();
    expect(root.getByText("askPanel.citations.title")).toBeTruthy();
    expect(root.getByText(/Unique excerpt for composed test/)).toBeTruthy();
  });
});
