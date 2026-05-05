import { describe, expect, it } from "vitest";
import {
  buildSpecialistStreamGroups,
  collectFormattedStreamLines,
  deriveRunState,
  formatStreamEventOneLine,
  pickLastMeaningfulStreamEvent,
  shouldOfferRunInspector,
  shouldShowSubagentRail,
} from "./agentRunViewModel.js";

const MOCK_T = {
  "chat.stream.intent": "Intent:{{cls}}:{{src}}",
  "chat.stream.intentNoSource": "Intent:{{cls}}",
  "chat.stream.route": "R:{{fr}}:{{to}}",
  "chat.stream.toolSearch": "{{spec}}|{{reason}}",
  "chat.stream.toolSearchSkipped": "{{spec}}|skip",
  "chat.stream.shortlistSkipped": "[skip]",
  "chat.stream.evidenceReady": "E:{{n}}",
  "chat.stream.contextCompacted": "M",
  "chat.stream.warningLine": "W:{{message}}",
  "chat.stream.warningLineWithCode": "W:{{label}}:{{message}}",
  "chat.stream.subagentStarted": "S+{{id}}",
  "chat.stream.subagentProgress": "P+{{id}}+{{summary}}",
  "chat.stream.subagentFinished": "S-{{id}}",
  "chat.stream.answerSynthesisStarted": "SYN+",
  "chat.stream.answerSynthesisFinished": "SYN-",
  "chat.stream.toolResultLabel": "TR",
  "chat.stream.rowsLabel": "rows",
  "chat.stream.errorLabel": "err",
  "chat.run.live.toolCall": "{{tool}}",
  "chat.run.live.toolCallQuery": "{{tool}}·{{q}}",
  "chat.run.answerClass.inventory": "Inventory list",
  "chat.run.intentSource.heuristic": "Heuristic",
  "chat.run.specialist.retrieval_agent": "Corpus search",
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

  it("treats answer_synthesis_finished as meaningful", () => {
    const events = [
      { type: "intent_classified", answer_class: "a", source: "h" },
      { type: "answer_synthesis_finished" },
    ];
    expect(pickLastMeaningfulStreamEvent(events)?.type).toBe("answer_synthesis_finished");
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
  it("formats intent_classified with localized class and visible source", () => {
    const line = formatStreamEventOneLine(t, { type: "intent_classified", answer_class: "inventory", source: "heuristic" });
    expect(line).toBe("Intent:Inventory list:Heuristic");
  });

  it("hides redundant intent source from headline", () => {
    const line = formatStreamEventOneLine(t, {
      type: "intent_classified",
      answer_class: "inventory",
      source: "single_agent_research_v1",
    });
    expect(line).toBe("Intent:Inventory list");
  });

  it("formats specialist_selected with localized roles", () => {
    expect(formatStreamEventOneLine(t, { type: "specialist_selected", from: "a", to: "b" })).toBe("R:A:B");
  });

  it("formats tool_search_result with skip via dedicated template", () => {
    expect(
      formatStreamEventOneLine(t, { type: "tool_search_result", specialist: "single_agent_react", reason: "r", skipped: true }),
    ).toBe("Single agent react|skip");
  });

  it("formats tool_search_result with localized reason and humanized fallback specialist", () => {
    expect(
      formatStreamEventOneLine(t, { type: "tool_search_result", specialist: "retrieval_agent", reason: "low_signal" }),
    ).toBe("Corpus search|Low signal");
  });

  it("formats evidence_ready", () => {
    expect(formatStreamEventOneLine(t, { type: "evidence_ready", citation_count: 2 })).toBe("E:2");
  });

  it("formats context_compacted without raw excerpt", () => {
    expect(formatStreamEventOneLine(t, { type: "context_compacted", session_summary_excerpt: "hello world" })).toBe("M");
  });

  it("formats warning with localized message and no raw code prefix", () => {
    expect(formatStreamEventOneLine(t, { type: "warning", code: "c", message: "msg" })).toBe("W:C:msg");
  });

  it("formats tool_call with query", () => {
    const line = formatStreamEventOneLine(t, {
      type: "tool_call",
      tool: "search",
      args_summary: { query: "papers about x" },
    });
    expect(line).toContain("papers about x");
    expect(line).toContain("chat.run.toolLabel.generic");
  });

  it("formats tool_result", () => {
    const line = formatStreamEventOneLine(t, { type: "tool_result", tool: "t", row_count: 3 });
    expect(line).toContain("TR");
    expect(line).toContain("rows: 3");
  });

  it("formats UI-5 subagent and synthesis events with localized id", () => {
    expect(formatStreamEventOneLine(t, { type: "subagent_started", subagent_id: "retrieval_agent" })).toBe("S+Corpus search");
    expect(
      formatStreamEventOneLine(t, { type: "subagent_progress", subagent_id: "r", summary: "search_chunks" }),
    ).toBe("P+R+Search chunks");
    expect(formatStreamEventOneLine(t, { type: "subagent_finished", subagent_id: "r" })).toBe("S-R");
    expect(formatStreamEventOneLine(t, { type: "answer_synthesis_started" })).toBe("SYN+");
    expect(formatStreamEventOneLine(t, { type: "answer_synthesis_finished" })).toBe("SYN-");
  });

  it("hides tool_search_result with reason=rules from headline picker", () => {
    const events = [
      { type: "intent_classified", answer_class: "inventory", source: "heuristic" },
      { type: "tool_search_result", specialist: "single_agent_react", reason: "rules" },
    ];
    expect(pickLastMeaningfulStreamEvent(events)?.type).toBe("intent_classified");
  });
});

describe("collectFormattedStreamLines", () => {
  it("returns chronological formatted lines capped at limit", () => {
    const events = Array.from({ length: 30 }, (_, i) => ({
      type: "intent_classified",
      answer_class: `c${i}`,
      source: "h",
    }));
    const lines = collectFormattedStreamLines(t, events, 5);
    expect(lines.length).toBe(5);
    expect(lines[0].toLowerCase()).toContain("c25");
  });
});

describe("shouldShowSubagentRail", () => {
  it("is false for empty stream", () => {
    expect(shouldShowSubagentRail([])).toBe(false);
  });

  it("is false when only a short orphan preamble", () => {
    expect(shouldShowSubagentRail([{ type: "intent_classified", answer_class: "x", source: "h" }])).toBe(false);
  });

  it("is true when orphan preamble has enough events", () => {
    expect(
      shouldShowSubagentRail([
        { type: "intent_classified", answer_class: "x", source: "h" },
        { type: "warning", code: "c", message: "m" },
        { type: "evidence_ready", citation_count: 1 },
      ]),
    ).toBe(true);
  });

  it("is true when specialist_selected exists", () => {
    expect(
      shouldShowSubagentRail([
        { type: "intent_classified", answer_class: "x", source: "h" },
        { type: "specialist_selected", from: "a", to: "b" },
      ]),
    ).toBe(true);
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
