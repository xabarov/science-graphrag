/** @vitest-environment jsdom */
import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { normalizeQueryResponse } from "../../../../services/researchApi.js";
import { AskAnswerPanel } from "./AskAnswerPanel.jsx";
import { renderAskAnswer } from "./AskAnswerPanel.testRender.jsx";

describe("AskAnswerPanel — agent tool trace", () => {
  it("shows compact tool trace in detailed agent mode after run", () => {
    const normalized = normalizeQueryResponse({
      answer: "Done",
      citations: [],
      graph_context: {},
      retrieval_trace: {},
    });
    const t = (k) => (k === "askPanel.toolTrace.title" ? "Tool trace" : k);
    renderAskAnswer(
      <AskAnswerPanel
        t={t}
        normalized={normalized}
        locked={false}
        inWorkspace={false}
        workId=""
        workspaceWorkId={null}
        retrievalMode="agent"
        agentToolTrace={[{ step: 1, tool: "web_search", duration_ms: 5, row_count: 2 }]}
        retrievalJsonOpen={false}
        onToggleRetrievalJson={() => {}}
        streamEvents={[]}
        isRunActive={false}
        chatDetailLevel="detailed"
      />,
    );
    expect(screen.getByTestId("ask-agent-tool-trace-block")).toBeTruthy();
    expect(screen.getByText("Tool trace")).toBeTruthy();
    expect(screen.getByText(/#1 web_search/)).toBeTruthy();
  });

  it("hides tool trace in simple mode", () => {
    const normalized = normalizeQueryResponse({
      answer: "Done",
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
        agentToolTrace={[{ step: 1, tool: "web_search", duration_ms: 5, row_count: 2 }]}
        retrievalJsonOpen={false}
        onToggleRetrievalJson={() => {}}
        streamEvents={[]}
        isRunActive={false}
        chatDetailLevel="simple"
      />,
    );
    expect(screen.queryByTestId("ask-agent-tool-trace-block")).toBeNull();
  });
});
