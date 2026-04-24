import { describe, expect, it } from "vitest";

import {
  edgeTypeCanvasLabel,
  getScienceGraphLegendNodeChipSx,
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

  it("hovered state strengthens stroke when not selected", () => {
    const base = getScienceGraphNodeStyle("Work", {});
    const hov = getScienceGraphNodeStyle("Work", { hovered: true });
    expect(hov.lineWidth).toBeGreaterThan(base.lineWidth);
  });

  it("selected wins over hovered", () => {
    const sel = getScienceGraphNodeStyle("Work", { selected: true, hovered: true });
    expect(sel.lineWidth).toBe(2);
  });

  it("falls back for unknown types", () => {
    const u = getScienceGraphNodeStyle("UnknownThing");
    expect(u.fill).toBeTruthy();
    expect(u.stroke).toBeTruthy();
  });

  it("dims external workspace membership vs internal", () => {
    const inner = getScienceGraphNodeStyle("Work", { workspaceMembership: "internal" });
    const outer = getScienceGraphNodeStyle("Work", { workspaceMembership: "external" });
    expect(outer.lineWidth).toBeLessThanOrEqual(inner.lineWidth);
    expect(outer.fill).not.toBe(inner.fill);
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

describe("getScienceGraphLegendNodeChipSx", () => {
  it("maps known node types to canvas palette", () => {
    const sx = getScienceGraphLegendNodeChipSx("Work");
    expect(sx.backgroundColor).toContain("99");
    expect(sx.border).toContain("129");
  });

  it("falls back for unknown types", () => {
    const sx = getScienceGraphLegendNodeChipSx("X");
    expect(sx.backgroundColor).toBeTruthy();
    expect(sx.border).toContain("255");
  });
});
