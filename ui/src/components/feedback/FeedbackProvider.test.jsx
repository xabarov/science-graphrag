/** @vitest-environment jsdom */
import { ThemeProvider } from "@mui/material/styles";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { buildAppTheme } from "../../theme/buildAppTheme.js";
import { FeedbackProvider } from "./FeedbackProvider.jsx";
import { useFeedback } from "./useFeedback.js";

const themeDark = buildAppTheme("dark");
const themeLight = buildAppTheme("light");

function ConfirmHarness() {
  const { confirm, showToast } = useFeedback();
  return (
    <button
      type="button"
      onClick={async () => {
        const ok = await confirm({
          title: "Confirm title",
          body: "Confirm body",
          variant: "danger",
          confirmLabel: "Do it",
          cancelLabel: "Back",
        });
        showToast(ok ? "confirmed" : "cancelled");
      }}
    >
      open-confirm
    </button>
  );
}

function PromptHarness() {
  const { prompt, showToast } = useFeedback();
  return (
    <button
      type="button"
      onClick={async () => {
        const v = await prompt({
          title: "Prompt title",
          label: "Name",
          defaultValue: "abc",
          confirmLabel: "Save",
          cancelLabel: "Back",
          validate: (raw) => (!String(raw).trim() ? "empty" : null),
        });
        showToast(v == null ? "prompt-null" : `prompt:${v}`);
      }}
    >
      open-prompt
    </button>
  );
}

afterEach(() => {
  cleanup();
});

describe("FeedbackProvider", () => {
  it("confirm resolves true and shows toast", async () => {
    render(
      <ThemeProvider theme={themeDark}>
        <FeedbackProvider>
          <ConfirmHarness />
        </FeedbackProvider>
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByText("open-confirm"));
    expect(await screen.findByText("Confirm body")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Do it" }));
    await waitFor(() => {
      expect(screen.getByText("confirmed")).toBeTruthy();
    });
  });

  it("prompt returns trimmed value when valid", async () => {
    render(
      <ThemeProvider theme={themeDark}>
        <FeedbackProvider>
          <PromptHarness />
        </FeedbackProvider>
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByText("open-prompt"));
    const input = await screen.findByLabelText("Name");
    fireEvent.change(input, { target: { value: "  trimmed  " } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => {
      expect(screen.getByText("prompt:trimmed")).toBeTruthy();
    });
  });

  it("confirm and toast work in light theme (tokenized overlays)", async () => {
    render(
      <ThemeProvider theme={themeLight}>
        <FeedbackProvider>
          <ConfirmHarness />
        </FeedbackProvider>
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByText("open-confirm"));
    expect(await screen.findByText("Confirm body")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Do it" }));
    await waitFor(() => {
      expect(screen.getByText("confirmed")).toBeTruthy();
    });
  });
});
