/** @vitest-environment jsdom */
import React from "react";
import { describe, expect, it, afterEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import AgentToolTrace from "./AgentToolTrace.jsx";

afterEach(() => {
  cleanup();
});

describe("AgentToolTrace", () => {
  it("renders tool steps and localized error when t is provided (mixed-case error)", () => {
    const t = (key) => {
      if (key === "askPanel.citation.fallback.host_not_allowed") return "URL blocked";
      return key;
    };
    render(
      <AgentToolTrace
        t={t}
        toolTrace={[
          { step: 1, tool: "web_fetch", duration_ms: 12, row_count: 0, error: "Host_Not_Allowed" },
        ]}
      />,
    );
    expect(screen.getByText(/#1 web_fetch/)).toBeTruthy();
    expect(screen.getByTestId("agent-tool-trace-error-0").textContent).toMatch(/URL blocked/);
  });

  it("renders raw error code when t is omitted", () => {
    render(
      <AgentToolTrace
        toolTrace={[
          { step: 1, tool: "web_fetch", duration_ms: 12, row_count: 0, error: "host_not_allowed" },
        ]}
      />,
    );
    expect(screen.getByText(/error=host_not_allowed/)).toBeTruthy();
  });
});
