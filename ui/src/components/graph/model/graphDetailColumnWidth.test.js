import { describe, expect, it } from "vitest";

import {
  clampGraphDetailColumnPx,
  GRAPH_DETAIL_COLUMN_PX_MAX,
  GRAPH_DETAIL_COLUMN_PX_MIN,
} from "./graphDetailColumnWidth.js";

describe("graphDetailColumnWidth", () => {
  it("clampGraphDetailColumnPx clamps to bounds and rounds", () => {
    expect(clampGraphDetailColumnPx(300)).toBe(300);
    expect(clampGraphDetailColumnPx(300.4)).toBe(300);
    expect(clampGraphDetailColumnPx(GRAPH_DETAIL_COLUMN_PX_MIN - 1)).toBe(GRAPH_DETAIL_COLUMN_PX_MIN);
    expect(clampGraphDetailColumnPx(GRAPH_DETAIL_COLUMN_PX_MAX + 9)).toBe(GRAPH_DETAIL_COLUMN_PX_MAX);
    expect(clampGraphDetailColumnPx(Number.NaN)).toBe(320);
  });
});
