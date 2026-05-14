/** @vitest-environment jsdom */
import { beforeEach, describe, expect, it } from "vitest";

import {
  LS_GRAPH_CANVAS_REPULSION,
  LS_GRAPH_DENSE_LABEL_HINT_DISMISSED,
  persistDenseLabelHintDismissed,
  persistRepulsionPercent,
  readDenseLabelHintDismissed,
  readRepulsionPercentStored,
} from "./graphCanvasMvpStorage.js";
import { REPULSION_DEFAULT_PERCENT } from "./physics/simConstants.js";

describe("graphCanvasMvpStorage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("readRepulsionPercentStored returns default when unset", () => {
    expect(readRepulsionPercentStored()).toBe(REPULSION_DEFAULT_PERCENT);
  });

  it("persistRepulsionPercent round-trips via localStorage", () => {
    persistRepulsionPercent(42);
    expect(window.localStorage.getItem(LS_GRAPH_CANVAS_REPULSION)).toBe("42");
    expect(readRepulsionPercentStored()).toBe(42);
  });

  it("readDenseLabelHintDismissed returns false when unset", () => {
    expect(readDenseLabelHintDismissed()).toBe(false);
  });

  it("persistDenseLabelHintDismissed round-trips via sessionStorage", () => {
    persistDenseLabelHintDismissed();
    expect(window.sessionStorage.getItem(LS_GRAPH_DENSE_LABEL_HINT_DISMISSED)).toBe("1");
    expect(readDenseLabelHintDismissed()).toBe(true);
  });
});
