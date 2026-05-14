import { describe, expect, it } from "vitest";

import { formatEvidenceSummaryForDisplay } from "./evidenceSummaryFormat.js";

function t(key, vars = {}) {
  const dict = {
    "chat.evidenceSummary.citationsOnly": "{{n}} cit",
    "chat.evidenceSummary.citationsAndTrace": "{{citations}} cit · {{steps}} tr",
    "chat.evidenceSummary.noCitations": "no cit",
    "chat.evidenceSummary.noCitationsWithTrace": "no cit · {{steps}} tr",
  };
  let out = dict[key] ?? key;
  Object.entries(vars || {}).forEach(([kk, v]) => {
    out = out.split(`{{${kk}}}`).join(String(v));
  });
  return out;
}

describe("formatEvidenceSummaryForDisplay", () => {
  it("parses citations-only envelope summary", () => {
    expect(formatEvidenceSummaryForDisplay(t, "3 citation(s)")).toBe("3 cit");
  });

  it("parses citations + trace steps", () => {
    expect(formatEvidenceSummaryForDisplay(t, "3 citation(s), 9 trace step(s)")).toBe("3 cit · 9 tr");
  });

  it("parses assistant reply without citations", () => {
    expect(formatEvidenceSummaryForDisplay(t, "assistant reply (no citations)")).toBe("no cit");
  });

  it("parses assistant reply + trace steps", () => {
    expect(formatEvidenceSummaryForDisplay(t, "assistant reply (no citations), 4 trace step(s)")).toBe("no cit · 4 tr");
  });

  it("returns unknown strings unchanged", () => {
    expect(formatEvidenceSummaryForDisplay(t, "custom note")).toBe("custom note");
  });
});
