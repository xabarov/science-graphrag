import { describe, expect, it, vi } from "vitest";

import { parseAgentSseJson } from "./agentStreamParse.js";

describe("parseAgentSseJson", () => {
  it("parses valid JSON", () => {
    expect(parseAgentSseJson('{"type":"tool_call","step":1}')).toEqual({ type: "tool_call", step: 1 });
  });

  it("returns null and notifies on invalid JSON", () => {
    const onParseError = vi.fn();
    expect(parseAgentSseJson("{not-json", { onParseError })).toBeNull();
    expect(onParseError).toHaveBeenCalled();
  });
});
