/** @vitest-environment node */
import { describe, expect, it } from "vitest";

import {
  buildLiveStatusPresentation,
  collectSafeExplanationLines,
  deriveHeaderProgressHint,
  formatStreamEventOneLine,
  liveStreamKindForType,
  mapToolNameToUserLabel,
  shouldSuppressPostRunStreamSummary,
} from "./agentRunViewModel.js";

function t(key, vars = {}) {
  const table = {
    "chat.run.productStep.searching_literature": "Searching works…",
    "chat.run.live.toolCall": "{{tool}}",
    "chat.run.live.toolCallQuery": "{{tool}} · {{q}}",
    "chat.stream.thinking": "Thinking…",
    "chat.run.toolLabel.idea_search": "Literature search",
    "chat.run.toolLabel.cypher_query": "Graph query",
    "chat.run.toolLabel.generic": "Tool: {{tool}}",
    "chat.run.productStep.using_tool": "Run {{tool}}",
    "chat.run.progressWorking": "Working…",
    "chat.run.liveExplain.routeReason": "R: {{reason}}",
    "chat.run.liveExplain.intentReason": "I {{cls}}: {{reason}}",
    "chat.run.liveExplain.subagentSummary": "S {{id}}: {{summary}}",
    "chat.stream.intent": "Intent:{{cls}} ({{src}})",
    "chat.stream.route": "Route:{{fr}} → {{to}}",
    "chat.stream.toolResultLabel": "result",
    "chat.stream.rowsLabel": "rows",
    "chat.stream.errorLabel": "err",
  };
  let out = table[key] || key;
  Object.entries(vars).forEach(([k, v]) => {
    out = out.split(`{{${k}}}`).join(String(v));
  });
  return out;
}

describe("liveStreamKindForType", () => {
  it("classifies known stream types", () => {
    expect(liveStreamKindForType("product_step")).toBe("primary");
    expect(liveStreamKindForType("tool_call")).toBe("secondary");
    expect(liveStreamKindForType("tool_result")).toBe("debug");
  });
});

describe("mapToolNameToUserLabel", () => {
  it("maps known tools and falls back", () => {
    expect(mapToolNameToUserLabel(t, "idea_search")).toBe("Literature search");
    expect(mapToolNameToUserLabel(t, "unknown_xyz")).toBe("Tool: unknown_xyz");
  });
});

describe("collectSafeExplanationLines", () => {
  it("collects truncated reasons without args", () => {
    const lines = collectSafeExplanationLines(
      t,
      [
        { type: "intent_classified", answer_class: "x", reason: "because" },
        { type: "specialist_selected", from: "a", to: "b", reason: "pick retrieval" },
      ],
      10,
    );
    // Single-word snake_case reason gets capitalized fallback ("Because"); prose is preserved.
    expect(lines.some((l) => l.toLowerCase().includes("because"))).toBe(true);
    expect(lines.some((l) => l.includes("pick retrieval"))).toBe(true);
  });
});

describe("buildLiveStatusPresentation", () => {
  it("uses product_step headline when present", () => {
    const pres = buildLiveStatusPresentation(
      t,
      [{ type: "product_step", code: "searching_literature", tool: "idea_search" }],
      true,
    );
    expect(pres.headline).toBe("Searching works…");
  });

  it("falls back to last tool_call when no meaningful primary", () => {
    const pres = buildLiveStatusPresentation(t, [{ type: "tool_call", step: 1, tool: "idea_search", args_summary: {} }], true);
    expect(pres.headline).toBe("Literature search");
    // Headline already equals the mapped tool label; chips must not repeat it.
    expect(pres.activityChips).toEqual([]);
  });

  it("excludes headline duplicate from recent lines", () => {
    const pres = buildLiveStatusPresentation(
      t,
      [
        { type: "intent_classified", answer_class: "inv", source: "h" },
        { type: "product_step", code: "searching_literature", tool: "idea_search" },
      ],
      false,
    );
    expect(pres.headline).toBe("Searching works…");
    expect(pres.recentLines.includes("Searching works…")).toBe(false);
    expect(pres.recentLines.some((l) => l.includes("Intent"))).toBe(true);
    expect(pres.showRecentToggle).toBe(true);
  });

  it("hides recent toggle when dedup removes all secondary lines", () => {
    const pres = buildLiveStatusPresentation(
      t,
      [{ type: "product_step", code: "searching_literature", tool: "idea_search" }],
      false,
    );
    expect(pres.headline).toBe("Searching works…");
    expect(pres.recentLines).toEqual([]);
    expect(pres.showRecentToggle).toBe(false);
  });

  it("keeps tool chips that differ from the product_step headline", () => {
    const pres = buildLiveStatusPresentation(
      t,
      [
        { type: "tool_call", step: 1, tool: "cypher_query", args_summary: {} },
        { type: "tool_call", step: 2, tool: "idea_search", args_summary: {} },
        { type: "product_step", code: "searching_literature", tool: "idea_search" },
      ],
      true,
    );
    expect(pres.headline).toBe("Searching works…");
    expect(pres.activityChips.some((c) => c.tool === "cypher_query" && c.label === "Graph query")).toBe(true);
    expect(pres.activityChips.every((c) => c.label.trim() !== pres.headline.trim())).toBe(true);
  });

  it("formats product_step using_tool with mapped tool label", () => {
    const line = formatStreamEventOneLine(t, {
      type: "product_step",
      code: "using_tool",
      tool: "idea_search",
    });
    expect(line).toBe("Run Literature search");
  });
});

describe("deriveHeaderProgressHint", () => {
  it("falls back to generic working line when hint would duplicate live headline", () => {
    const events = [{ type: "product_step", code: "searching_literature", tool: "idea_search" }];
    const hint = deriveHeaderProgressHint(t, events, true);
    expect(hint).toBe("Working…");
  });

  it("falls back to working line when tool headline matches progress hint", () => {
    const events = [{ type: "tool_call", step: 1, tool: "idea_search", args_summary: {} }];
    const hint = deriveHeaderProgressHint(t, events, true);
    expect(hint).toBe("Working…");
  });
});

describe("shouldSuppressPostRunStreamSummary", () => {
  it("is true when the last meaningful event is answer_synthesis_finished", () => {
    expect(
      shouldSuppressPostRunStreamSummary([
        { type: "product_step", code: "searching_literature" },
        { type: "answer_synthesis_finished" },
      ]),
    ).toBe(true);
  });

  it("is false when the run ends on another meaningful type", () => {
    expect(shouldSuppressPostRunStreamSummary([{ type: "product_step", code: "searching_literature" }])).toBe(false);
  });
});
