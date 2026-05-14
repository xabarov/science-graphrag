import { describe, expect, it } from "vitest";

import { graphDetailClaimBodySx, graphDetailCodePreSx, graphDetailMarkdownPanelSx } from "./graphNodeDetailSectionSx.js";

describe("graphNodeDetailSectionSx", () => {
  const tk = {
    text: { primary: "#fff", secondary: "#888" },
    border: { default: "#333" },
    surface: { sidebar: "#111", code: "#000" },
  };

  it("graphDetailClaimBodySx includes maxHeight for compact", () => {
    const sx = graphDetailClaimBodySx(tk, true);
    expect(sx.maxHeight).toBe(220);
    expect(graphDetailClaimBodySx(tk, false).maxHeight).toBe(320);
  });

  it("graphDetailMarkdownPanelSx scales with compact", () => {
    expect(graphDetailMarkdownPanelSx(tk, true).maxHeight).toBe(260);
    expect(graphDetailMarkdownPanelSx(tk, false).maxHeight).toBe(360);
  });

  it("graphDetailCodePreSx uses code surface", () => {
    const sx = graphDetailCodePreSx(tk, false);
    expect(sx.backgroundColor).toBe(tk.surface.code);
  });
});
