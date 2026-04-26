/** @vitest-environment jsdom */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { ChatComposer } from "./ChatComposer.jsx";

const theme = createTheme();

afterEach(() => {
  cleanup();
});

describe("ChatComposer", () => {
  it("opens answer mode menu from toolbar icon and applies selection", () => {
    const onAnswerClassHintChange = vi.fn();
    render(
      <MemoryRouter>
        <ThemeProvider theme={theme}>
          <ChatComposer
            t={(key, vars) => (vars?.label ? `${key}:${vars.label}` : key)}
            query="test"
            onQueryChange={() => {}}
            loading={false}
            onSubmit={(e) => e.preventDefault()}
            inWorkspace={false}
            standaloneChatPath="/chat"
            locked={false}
            workspaceId=""
            workId=""
            onWorkIdChange={() => {}}
            onArticlePicked={() => {}}
            onWorkSearch={async () => []}
            resolvedWork={null}
            corpusWorkspaceOnly={false}
            standaloneMode
            answerClassHint=""
            onAnswerClassHintChange={onAnswerClassHintChange}
          />
        </ThemeProvider>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "chat.answerMode.openMenuAria" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "chat.answerMode.inventory" }));

    expect(onAnswerClassHintChange).toHaveBeenCalledWith("inventory");
  });
});
