import { describe, expect, it } from "vitest";
import { deriveAgentLiveStatusChrome } from "./agentLiveStatusChrome.js";

describe("deriveAgentLiveStatusChrome", () => {
  const basePresentation = {
    activityChips: [{ tool: "a", label: "A" }, { tool: "b", label: "B" }, { tool: "c", label: "C" }],
    showRecentToggle: true,
    showExplainToggle: true,
  };

  it("returns empty chips and toggles when embedded", () => {
    const out = deriveAgentLiveStatusChrome(basePresentation, { chatDetailLevel: "detailed", embedded: true });
    expect(out.minimalEmbeddedChrome).toBe(true);
    expect(out.activityChips).toEqual([]);
    expect(out.showRecentToggle).toBe(true);
    expect(out.showExplainToggle).toBe(true);
  });

  it("caps chips at two in simple mode when not embedded", () => {
    const out = deriveAgentLiveStatusChrome(basePresentation, { chatDetailLevel: "simple", embedded: false });
    expect(out.isSimple).toBe(true);
    expect(out.activityChips).toHaveLength(2);
    expect(out.showRecentToggle).toBe(false);
    expect(out.showExplainToggle).toBe(false);
  });

  it("handles null presentation safely", () => {
    const out = deriveAgentLiveStatusChrome(null, { chatDetailLevel: "detailed", embedded: false });
    expect(out.activityChips).toEqual([]);
    expect(out.isSimple).toBe(false);
    expect(out.showRecentToggle).toBe(false);
  });

  it("treats non-array activityChips as empty", () => {
    const out = deriveAgentLiveStatusChrome(
      { ...basePresentation, activityChips: /** @type {unknown} */ (undefined) },
      { chatDetailLevel: "detailed", embedded: false },
    );
    expect(out.activityChips).toEqual([]);
  });
});
