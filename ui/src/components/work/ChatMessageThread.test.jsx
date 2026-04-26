/** @vitest-environment jsdom */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatMessageThread } from "./ChatMessageThread.jsx";

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

const theme = createTheme();

const baseProps = {
  t: (k) => k,
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

describe("ChatMessageThread", () => {
  it("shows empty state when there is no history and no pending query", () => {
    render(
      <ThemeProvider theme={theme}>
        <ChatMessageThread {...baseProps} />
      </ThemeProvider>,
    );
    expect(screen.getByText("chat.thread.emptyTitle")).toBeTruthy();
    expect(screen.getByText("chat.thread.emptySubtitle")).toBeTruthy();
  });
});
