/** @vitest-environment jsdom */
import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { normalizeQueryResponse } from "../../../../services/researchApi.js";
import { AskAnswerPanel } from "./AskAnswerPanel.jsx";
import { renderAskAnswer } from "./AskAnswerPanel.testRender.jsx";

describe("AskAnswerPanel — alerts", () => {
  it("shows degraded info alert when graph_context has degraded", () => {
    const normalized = normalizeQueryResponse({
      answer: "A",
      citations: [],
      graph_context: { degraded: ["x"] },
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
    expect(screen.getByText("askPanel.answer.degraded")).toBeTruthy();
  });

  it("renders normalized warnings", () => {
    const normalized = normalizeQueryResponse({
      answer: "ok",
      citations: [],
      graph_context: {},
      retrieval_trace: {},
      warnings: ["no_workspace"],
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
    expect(screen.getByText(partialMsg)).toBeTruthy();
    expect(screen.getByText(followMsg)).toBeTruthy();
  });
});
