import { describe, expect, it } from "vitest";

import { preserveGraphPageOptionalParams, readGraphPageLayoutFlags } from "./graphPageUrl.js";

describe("graphPageUrl", () => {
  it("readGraphPageLayoutFlags parses compact and focus", () => {
    expect(readGraphPageLayoutFlags(new URLSearchParams())).toEqual({
      compact: false,
      focus: false,
      compactLayout: false,
    });
    expect(readGraphPageLayoutFlags(new URLSearchParams("compact=1"))).toEqual({
      compact: true,
      focus: false,
      compactLayout: true,
    });
    expect(readGraphPageLayoutFlags(new URLSearchParams("focus=1"))).toEqual({
      compact: false,
      focus: true,
      compactLayout: true,
    });
    expect(readGraphPageLayoutFlags(new URLSearchParams("compact=1&focus=1"))).toEqual({
      compact: true,
      focus: true,
      compactLayout: true,
    });
  });

  it("preserveGraphPageOptionalParams copies lab, compact, focus", () => {
    const prev = new URLSearchParams("lab=1&compact=1&focus=1&work_id=w1");
    const params = new URLSearchParams();
    params.set("work_id", "w2");
    preserveGraphPageOptionalParams(params, prev);
    expect(params.get("work_id")).toBe("w2");
    expect(params.get("lab")).toBe("1");
    expect(params.get("compact")).toBe("1");
    expect(params.get("focus")).toBe("1");
  });

  it("preserveGraphPageOptionalParams skips absent flags", () => {
    const prev = new URLSearchParams("work_id=w1");
    const params = new URLSearchParams();
    preserveGraphPageOptionalParams(params, prev);
    expect([...params.keys()].sort()).toEqual([]);
  });
});
