import { describe, expect, it } from "vitest";

import {
  edgeTypeCanvasLabel,
  edgeTypeCanvasLabelFromEdge,
  getScienceGraphLegendNodeChipSx,
  getScienceGraphNodeStyle,
  getScienceGraphNodeTypeIcon,
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

  it("replaces underscores in raw Neo4j-style types by default", () => {
    expect(edgeTypeCanvasLabel("HAS_AUTHORSHIP")).toBe("HAS AUTHORSHIP");
  });

  it("preserves underscores for backend display strings when opted out", () => {
    expect(edgeTypeCanvasLabel("is_author_of", { normalizeUnderscores: false })).toBe("is_author_of");
  });

  it("passes through spaced display strings when opted out", () => {
    expect(edgeTypeCanvasLabel("is author of", { normalizeUnderscores: false })).toBe("is author of");
  });
});

describe("edgeTypeCanvasLabelFromEdge", () => {
  it("prefers displayType over raw type", () => {
    expect(edgeTypeCanvasLabelFromEdge({ displayType: "cites", type: "CITES" })).toBe("cites");
  });

  it("treats whitespace-only displayType as absent", () => {
    expect(edgeTypeCanvasLabelFromEdge({ displayType: "   ", type: "CITES" })).toBe("CITES");
  });

  it("normalizes underscores when falling back to type", () => {
    expect(edgeTypeCanvasLabelFromEdge({ displayType: "", type: "HAS_AUTHORSHIP" })).toBe("HAS AUTHORSHIP");
  });
});

describe("getScienceGraphNodeTypeIcon", () => {
  it("returns a renderable component for known node kinds", () => {
    const workIcon = getScienceGraphNodeTypeIcon("Work");
    const internalIcon = getScienceGraphNodeTypeIcon("WorkInternal");
    expect(workIcon).toBeTruthy();
    expect(internalIcon).toBeTruthy();
    expect(["function", "object"]).toContain(typeof workIcon);
    expect(getScienceGraphNodeTypeIcon("UnknownX")).toBeNull();
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
