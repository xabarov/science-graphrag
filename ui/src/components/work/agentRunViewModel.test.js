import { describe, expect, it } from "vitest";
import {
  buildSpecialistStreamGroups,
  deriveRunState,
  formatStreamEventOneLine,
  pickLastMeaningfulStreamEvent,
  shouldOfferRunInspector,
} from "./agentRunViewModel.js";

const MOCK_T = {
  "chat.stream.intent": "Intent:{{cls}}:{{src}}",
  "chat.stream.route": "R:{{fr}}:{{to}}",
  "chat.stream.toolSearch": "{{spec}}|{{reason}}",
  "chat.stream.shortlistSkipped": "[skip]",
  "chat.stream.evidenceReady": "E:{{n}}",
  "chat.stream.contextCompacted": "M:{{excerpt}}",
  "chat.stream.warningLine": "W:{{code}}:{{message}}",
  "chat.stream.toolResultLabel": "TR",
  "chat.stream.rowsLabel": "rows",
  "chat.stream.errorLabel": "err",
  "chat.run.live.toolCall": "{{tool}}",
  "chat.run.live.toolCallQuery": "{{tool}}·{{q}}",
};

function t(key, vars = {}) {
  let out = MOCK_T[key] || key;
  Object.entries(vars).forEach(([k, v]) => {
    out = out.split(`{{${k}}}`).join(String(v));
  });
  return out;
}

describe("pickLastMeaningfulStreamEvent", () => {
  it("ignores tool_call noise and picks higher-level events", () => {
    const events = [
      { type: "tool_call", tool: "x" },
      { type: "intent_classified", answer_class: "inventory", source: "heuristic" },
    ];
    expect(pickLastMeaningfulStreamEvent(events)).toEqual(events[1]);
  });

  it("returns last meaningful by order", () => {
    const events = [
      { type: "intent_classified", answer_class: "a", source: "h" },
      { type: "evidence_ready", citation_count: 3 },
    ];
    expect(pickLastMeaningfulStreamEvent(events)?.type).toBe("evidence_ready");
  });
});

describe("deriveRunState", () => {
  it("marks running when active", () => {
    expect(deriveRunState({ normalized: { warnings: [] }, isRunActive: true, streamEvents: [] }).runState).toBe("running");
  });

  it("marks warning from stream warnings", () => {
    const r = deriveRunState({
      normalized: { warnings: [] },
      isRunActive: false,
      streamEvents: [{ type: "warning", code: "x", message: "m" }],
    });
    expect(r.runState).toBe("warning");
  });

  it("marks failed when stream contains error event", () => {
    expect(
      deriveRunState({
        normalized: { warnings: [] },
        isRunActive: false,
        streamEvents: [{ type: "error", detail: "x" }],
      }).runState,
    ).toBe("failed");
  });

  it("prefers failed over warning when both present", () => {
    expect(
      deriveRunState({
        normalized: { warnings: ["no_workspace"] },
        isRunActive: false,
        streamEvents: [{ type: "error", detail: "bad" }, { type: "warning", code: "c", message: "m" }],
      }).runState,
    ).toBe("failed");
  });

  it("marks degraded from normalized flags when no warnings", () => {
    expect(
      deriveRunState({
        normalized: {
          warnings: [],
          graph_context: { degraded: ["x"] },
          retrieval_trace: {},
        },
        isRunActive: false,
        streamEvents: [],
      }).runState,
    ).toBe("degraded");
  });

  it("marks warning from normalized warnings over degraded", () => {
    expect(
      deriveRunState({
        normalized: {
          warnings: ["weak_evidence"],
          graph_context: { degraded: ["x"] },
          retrieval_trace: {},
        },
        isRunActive: false,
        streamEvents: [],
      }).runState,
    ).toBe("warning");
  });
});

describe("shouldOfferRunInspector", () => {
  it("is false outside agent mode", () => {
    expect(shouldOfferRunInspector({ retrievalMode: "vector", normalized: { answer: "a" } })).toBe(false);
  });

  it("is true when retrieval trace has hits", () => {
    expect(
      shouldOfferRunInspector({
        retrievalMode: "agent",
        normalized: { answer: "a", retrieval_trace: { hit_count: 2 } },
        streamEvents: [],
        agentToolTrace: [],
      }),
    ).toBe(true);
  });

  it("is true when stream events exist", () => {
    expect(
      shouldOfferRunInspector({
        retrievalMode: "agent",
        normalized: { answer: "a" },
        streamEvents: [{ type: "intent_classified" }],
        agentToolTrace: [],
      }),
    ).toBe(true);
  });

  it("is false for bare normalized answer without rich signals", () => {
    expect(
      shouldOfferRunInspector({
        retrievalMode: "agent",
        normalized: { answer: "only" },
        streamEvents: [],
        agentToolTrace: [],
      }),
    ).toBe(false);
  });
});

describe("formatStreamEventOneLine", () => {
  it("formats intent_classified", () => {
    const line = formatStreamEventOneLine(t, { type: "intent_classified", answer_class: "inventory", source: "heuristic" });
    expect(line).toBe("Intent:inventory:heuristic");
  });

  it("formats specialist_selected", () => {
    expect(formatStreamEventOneLine(t, { type: "specialist_selected", from: "a", to: "b" })).toBe("R:a:b");
  });

  it("formats tool_search_result with skip", () => {
    expect(formatStreamEventOneLine(t, { type: "tool_search_result", specialist: "s", reason: "r", skipped: true })).toBe("s|r [skip]");
  });

  it("formats evidence_ready", () => {
    expect(formatStreamEventOneLine(t, { type: "evidence_ready", citation_count: 2 })).toBe("E:2");
  });

  it("formats context_compacted with excerpt", () => {
    expect(formatStreamEventOneLine(t, { type: "context_compacted", session_summary_excerpt: "hello world" })).toBe("M:hello world");
  });

  it("formats warning", () => {
    expect(formatStreamEventOneLine(t, { type: "warning", code: "c", message: "msg" })).toBe("W:c:msg");
  });

  it("formats tool_call with query", () => {
    expect(formatStreamEventOneLine(t, { type: "tool_call", tool: "search", args_summary: { query: "papers about x" } })).toContain("search");
  });

  it("formats tool_result", () => {
    const line = formatStreamEventOneLine(t, { type: "tool_result", tool: "t", row_count: 3 });
    expect(line).toContain("TR");
    expect(line).toContain("rows: 3");
  });
});

describe("buildSpecialistStreamGroups", () => {
  it("groups events after specialist_selected", () => {
    const events = [
      { type: "intent_classified", answer_class: "x", source: "h" },
      { type: "specialist_selected", from: "sup", to: "ret" },
      { type: "tool_call", tool: "idea_search" },
    ];
    const g = buildSpecialistStreamGroups(events);
    expect(g.length).toBe(2);
    expect(g[0].isOrphan).toBe(true);
    expect(g[1].to).toBe("ret");
    expect(g[1].events.length).toBe(2);
  });
});
