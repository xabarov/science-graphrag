/** @vitest-environment jsdom */
import React from "react";
import { ThemeProvider } from "@mui/material/styles";
import { MemoryRouter } from "react-router-dom";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../i18n/I18nContext.jsx";
import { buildAppTheme } from "../theme/buildAppTheme.js";
import * as setupHintsApi from "../services/setupHintsApi.js";
import HomePage from "./HomePage.jsx";

vi.mock("../services/setupHintsApi.js", () => ({
  getSetupHints: vi.fn(),
}));

const theme = buildAppTheme("dark");

function renderHome() {
  return render(
    <MemoryRouter>
      <ThemeProvider theme={theme}>
        <I18nProvider>
          <HomePage />
        </I18nProvider>
      </ThemeProvider>
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
});

describe("HomePage setup hints", () => {
  beforeEach(() => {
    vi.mocked(setupHintsApi.getSetupHints).mockReset();
  });

  it("shows setup card when needs_initial_setup", async () => {
    vi.mocked(setupHintsApi.getSetupHints).mockResolvedValue({
      needs_initial_setup: true,
      llm_api_key_configured: false,
      vl_api_key_configured: false,
    });
    renderHome();
    await waitFor(() => {
      expect(screen.getByText(/Add your API key for full extraction/i)).toBeTruthy();
    });
  });

  it("hides setup card when LLM is configured", async () => {
    vi.mocked(setupHintsApi.getSetupHints).mockResolvedValue({
      needs_initial_setup: false,
      llm_api_key_configured: true,
      vl_api_key_configured: true,
    });
    renderHome();
    await waitFor(() => {
      expect(setupHintsApi.getSetupHints).toHaveBeenCalled();
    });
    expect(screen.queryByText(/Add your API key for full extraction/i)).toBeNull();
  });
});
