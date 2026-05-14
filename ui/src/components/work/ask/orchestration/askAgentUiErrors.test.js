/** @vitest-environment node */
import { describe, expect, it } from "vitest";

import { formatAskAgentUiError } from "./askAgentUiErrors.js";

describe("formatAskAgentUiError", () => {
  const t = (key) => key;

  it("returns incomplete-turn message for empty input", () => {
    expect(formatAskAgentUiError(t, "")).toBe("askPanel.agentIncompleteTurn");
    expect(formatAskAgentUiError(t, "   ")).toBe("askPanel.agentIncompleteTurn");
  });

  it("maps 403 upstream LLM to forbidden copy", () => {
    expect(formatAskAgentUiError(t, "Upstream LLM error (code 403)")).toBe("chat.errors.llmForbidden");
    expect(formatAskAgentUiError(t, "403 something Upstream LLM")).toBe("chat.errors.llmForbidden");
  });

  it("maps 401 upstream LLM to unauthorized copy", () => {
    expect(formatAskAgentUiError(t, "Upstream LLM error (code 401)")).toBe("chat.errors.llmUnauthorized");
  });

  it("passes through other messages", () => {
    expect(formatAskAgentUiError(t, "custom")).toBe("custom");
  });
});
