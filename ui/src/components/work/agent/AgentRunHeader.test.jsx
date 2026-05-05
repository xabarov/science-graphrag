/** @vitest-environment jsdom */
import { ThemeProvider } from "@mui/material/styles";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { buildAppTheme } from "../../../theme/buildAppTheme.js";
import { AgentRunHeader } from "./AgentRunHeader.jsx";

const theme = buildAppTheme("dark");

afterEach(() => {
  cleanup();
});

function renderHeader(runState, extra = {}) {
  return render(
    <ThemeProvider theme={theme}>
      <AgentRunHeader t={(k) => k} runState={runState} progressHint="" {...extra} />
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

  it("shows progress hint while running when provided", () => {
    render(
      <ThemeProvider theme={theme}>
        <AgentRunHeader t={(k) => k} runState="running" progressHint="Working…" />
      </ThemeProvider>,
    );
    expect(screen.getByText("Working…")).toBeTruthy();
  });

  it("does not render answer-class expand affordance", () => {
    renderHeader("done");
    expect(screen.queryByRole("button", { name: "chat.run.headerDetailsExpandAria" })).toBeNull();
  });
});
