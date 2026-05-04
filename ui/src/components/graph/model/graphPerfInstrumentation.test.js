/** @vitest-environment jsdom */
import { describe, expect, it } from "vitest";

import { isGraphPerfMarksEnabled, measureGraphStage } from "./graphPerfInstrumentation.js";

describe("graphPerfInstrumentation", () => {
  it("returns fn result when perf marks are disabled", () => {
    expect(isGraphPerfMarksEnabled()).toBe(false);
    expect(
      measureGraphStage("test.stage", () => 42),
    ).toBe(42);
  });
});
