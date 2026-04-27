/** @vitest-environment jsdom */
import { ThemeProvider } from "@mui/material/styles";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MemoryRouter } from "react-router-dom";

import { normalizeQueryResponse } from "../../services/researchApi.js";
import { buildAppTheme } from "../../theme/buildAppTheme.js";
import { FeedbackProvider } from "../feedback/FeedbackProvider.jsx";
import { ChatMessageThread } from "./ChatMessageThread.jsx";

const theme = buildAppTheme("dark");

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
  cleanup();
});

const baseProps = {
  t: (k) => k,
  scopeKey: "scope-a",
  activeSessionId: "sess-1",
  streamingTarget: null,
  history: [],
  pendingUserQuery: "",
  isLoading: false,
  streamEvents: [],
  liveNormalized: null,
  locked: false,
  inWorkspace: false,
  workId: "",
  workspaceWorkId: null,
  agentToolTrace: [],
  retrievalJsonOpen: false,
  onToggleRetrievalJson: () => {},
};

function renderThread(ui) {
  return render(
    <MemoryRouter>
      <ThemeProvider theme={theme}>
        <FeedbackProvider>{ui}</FeedbackProvider>
      </ThemeProvider>
    </MemoryRouter>,
  );
}

describe("ChatMessageThread", () => {
  it("shows empty state when there is no history and no pending query", () => {
    renderThread(<ChatMessageThread {...baseProps} />);
    expect(screen.getByText("chat.thread.emptyTitle")).toBeTruthy();
    expect(screen.getByText("chat.thread.emptySubtitle")).toBeTruthy();
  });

  it("does not show pending/live run when streamingTarget targets another session", () => {
    renderThread(
      <ChatMessageThread
        {...baseProps}
        pendingUserQuery="hello"
        isLoading
        streamingTarget={{ scopeKey: "scope-a", sessionId: "other-session" }}
      />,
    );
    expect(screen.getByText("chat.thread.emptyTitle")).toBeTruthy();
  });

  it("shows pending user bubble when streamingTarget matches scope and session", () => {
    renderThread(
      <ChatMessageThread
        {...baseProps}
        pendingUserQuery="hello"
        isLoading
        streamingTarget={{ scopeKey: "scope-a", sessionId: "sess-1" }}
      />,
    );
    expect(screen.getByText("hello")).toBeTruthy();
  });

  it("hides empty answer chrome while streaming pending assistant turn", () => {
    const live = normalizeQueryResponse({
      answer: "",
      citations: [],
      graph_context: {},
      retrieval_trace: {},
    });
    renderThread(
      <ChatMessageThread
        {...baseProps}
        pendingUserQuery="question"
        isLoading
        streamingTarget={{ scopeKey: "scope-a", sessionId: "sess-1" }}
        liveNormalized={live}
        streamEvents={[{ type: "product_step", code: "searching_literature", tool: "idea_search" }]}
      />,
    );
    expect(screen.queryByText("chat.run.answerSectionTitle")).toBeNull();
    expect(screen.queryByTestId("ask-answer-markdown")).toBeNull();
    expect(screen.queryByText("askPanel.citations.title")).toBeNull();
  });

  it("renders copy and restart actions for saved turns", async () => {
    const onRestartFromTurn = vi.fn();
    const onCopyAssistantEntry = vi.fn();
    const onDeleteTurn = vi.fn();
    renderThread(
      <ChatMessageThread
        {...baseProps}
        history={[{ id: "t1", query: "hello world", answer: "", details: { answer: "assistant body" } }]}
        onRestartFromTurn={onRestartFromTurn}
        onCopyAssistantEntry={onCopyAssistantEntry}
        onDeleteTurn={onDeleteTurn}
      />,
    );
    const btnByAria = (label) =>
      screen.getAllByLabelText(label).find((el) => el.tagName === "BUTTON" && el.getAttribute("type") === "button");
    expect(btnByAria("chat.thread.actions.retryAria")).toBeTruthy();
    expect(btnByAria("chat.thread.actions.copyAria")).toBeTruthy();
    expect(btnByAria("chat.thread.actions.metadataAria")).toBeTruthy();
    expect(btnByAria("chat.thread.actions.deleteAria")).toBeTruthy();
    fireEvent.click(btnByAria("chat.thread.actions.retryAria"));
    expect(onRestartFromTurn).toHaveBeenCalledWith("t1");
    fireEvent.click(btnByAria("chat.thread.actions.copyAria"));
    expect(onCopyAssistantEntry).toHaveBeenCalled();
    fireEvent.click(btnByAria("chat.thread.actions.metadataAria"));
    expect(screen.getByText("chat.thread.meta.title")).toBeTruthy();
    fireEvent.click(btnByAria("chat.thread.actions.deleteAria"));
    expect(await screen.findByText("chat.thread.deleteTurnDialogTitle")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "chat.sidebar.deleteConfirmButton" }));
    await waitFor(() => {
      expect(onDeleteTurn).toHaveBeenCalledWith("t1");
    });
  });
});
