/** @vitest-environment jsdom */
import { cleanup, render, screen } from "@testing-library/react";
import { ThemeProvider } from "@mui/material/styles";
import { afterEach, describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { buildAppTheme } from "../../../theme/buildAppTheme.js";
import { ChatComposer } from "./ChatComposer.jsx";

const theme = buildAppTheme("dark");

afterEach(() => {
  cleanup();
});

describe("ChatComposer", () => {
  it("disables send when query is empty", () => {
    render(
      <MemoryRouter>
        <ThemeProvider theme={theme}>
          <ChatComposer
            t={(key) => key}
            query=""
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
          />
        </ThemeProvider>
      </MemoryRouter>,
    );

    const send = screen.getByRole("button", { name: "chat.composer.sendAria" });
    expect(send).toBeInstanceOf(HTMLButtonElement);
    expect(send.disabled).toBe(true);
  });
});
