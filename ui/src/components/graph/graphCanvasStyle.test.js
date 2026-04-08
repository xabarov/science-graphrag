import { describe, expect, it } from "vitest";

import {
  edgeTypeCanvasLabel,
  getScienceGraphNodeStyle,
  truncateCanvasLabel,
} from "./graphCanvasStyle.js";

describe("getScienceGraphNodeStyle", () => {
  it("returns distinct styles for known types", () => {
    const w = getScienceGraphNodeStyle("Work");
    const m = getScienceGraphNodeStyle("Method");
    expect(w.fill).not.toBe(m.fill);
  });

  it("selected state uses highlight stroke", () => {
    const base = getScienceGraphNodeStyle("Dataset", { selected: false });
    const sel = getScienceGraphNodeStyle("Dataset", { selected: true });
    expect(sel.lineWidth).toBeGreaterThan(base.lineWidth);
    expect(sel.stroke).toContain("255");
  });

  it("falls back for unknown types", () => {
    const u = getScienceGraphNodeStyle("UnknownThing");
    expect(u.fill).toBeTruthy();
    expect(u.stroke).toBeTruthy();
  });
});

describe("truncateCanvasLabel", () => {
  it("returns em dash for empty", () => {
    expect(truncateCanvasLabel("")).toBe("—");
    expect(truncateCanvasLabel("   ")).toBe("—");
  });

  it("truncates long strings", () => {
    const s = "a".repeat(40);
    expect(truncateCanvasLabel(s, 10).length).toBeLessThanOrEqual(10);
    expect(truncateCanvasLabel(s, 10).endsWith("…")).toBe(true);
  });
});

describe("edgeTypeCanvasLabel", () => {
  it("passes through short types", () => {
    expect(edgeTypeCanvasLabel("CITES")).toBe("CITES");
  });
});
