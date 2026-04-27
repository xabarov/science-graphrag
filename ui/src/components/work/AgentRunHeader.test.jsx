/** @vitest-environment jsdom */
import { ThemeProvider } from "@mui/material/styles";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { buildAppTheme } from "../../theme/buildAppTheme.js";
import { AgentRunHeader } from "./AgentRunHeader.jsx";

const theme = buildAppTheme("dark");

function renderHeader(runState) {
  return render(
    <ThemeProvider theme={theme}>
      <AgentRunHeader
        t={(k) => k}
        runState={runState}
        answerClass={null}
        citationCount={0}
        durationMs={null}
        streamEventCount={0}
      />
    </ThemeProvider>,
  );
}

describe("AgentRunHeader", () => {
  it("renders state chip for running", () => {
    renderHeader("running");
    expect(screen.getByText("chat.run.state.running")).toBeTruthy();
  });

  it("renders state chip for done", () => {
    renderHeader("done");
    expect(screen.getByText("chat.run.state.done")).toBeTruthy();
  });

  it("renders state chip for warning", () => {
    renderHeader("warning");
    expect(screen.getByText("chat.run.state.warning")).toBeTruthy();
  });

  it("renders state chip for degraded", () => {
    renderHeader("degraded");
    expect(screen.getByText("chat.run.state.degraded")).toBeTruthy();
  });

  it("renders state chip for failed", () => {
    renderHeader("failed");
    expect(screen.getByText("chat.run.state.failed")).toBeTruthy();
  });
});
