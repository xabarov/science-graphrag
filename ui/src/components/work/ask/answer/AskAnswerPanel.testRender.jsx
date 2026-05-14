/** @vitest-environment jsdom */
import { ThemeProvider } from "@mui/material/styles";
import { cleanup, render } from "@testing-library/react";
import { afterEach } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { buildAppTheme } from "../../../../theme/buildAppTheme.js";

export const askAnswerTestTheme = buildAppTheme("dark");

export function renderAskAnswer(ui) {
  return render(
    <MemoryRouter>
      <ThemeProvider theme={askAnswerTestTheme}>{ui}</ThemeProvider>
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
});
