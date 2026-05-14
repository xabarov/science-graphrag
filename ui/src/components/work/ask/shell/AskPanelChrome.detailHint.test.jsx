/** @vitest-environment jsdom */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { ThemeProvider } from "@mui/material/styles";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { buildAppTheme } from "../../../../theme/buildAppTheme.js";
import {
  readChatDetailDiscoveryHintDismissed,
  writeChatDetailDiscoveryHintDismissed,
} from "../chat/chatUiPreferences.js";
import { AskPanelChrome } from "./AskPanelChrome.jsx";

const theme = buildAppTheme("dark");

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("AskPanelChrome detail discovery hint", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("shows one-shot tooltip when detail is simple and hint was not dismissed", () => {
    const onToggle = vi.fn();
    render(
      <ThemeProvider theme={theme}>
        <AskPanelChrome
          showPageChrome={false}
          t={(k) => k}
          scopeEyebrow="scope"
          error={null}
          detailLevel="simple"
          onToggleDetailLevel={onToggle}
        />
      </ThemeProvider>,
    );
    expect(screen.getByText("chat.chrome.detailDiscoveryHint")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "chat.chrome.detailToggleAria" }));
    expect(onToggle).toHaveBeenCalledTimes(1);
    expect(readChatDetailDiscoveryHintDismissed()).toBe(true);
  });

  it("does not show tooltip when hint was already dismissed", () => {
    writeChatDetailDiscoveryHintDismissed();
    render(
      <ThemeProvider theme={theme}>
        <AskPanelChrome
          showPageChrome={false}
          t={(k) => k}
          scopeEyebrow="scope"
          error={null}
          detailLevel="simple"
          onToggleDetailLevel={() => {}}
        />
      </ThemeProvider>,
    );
    expect(screen.queryByText("chat.chrome.detailDiscoveryHint")).toBeNull();
  });
});
