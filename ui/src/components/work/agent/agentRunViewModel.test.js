import { describe, expect, it } from "vitest";
import {
  aggregateRepeatedEvents,
  buildLiveStatusPresentation,
  buildSpecialistStreamGroups,
  collectFormattedStreamLines,
  collectRecentToolNamesForChips,
  collectSafeExplanationLines,
  deriveDecisionRationale,
  derivePrimaryHeadline,
  deriveRunState,
  formatAggregatedEventOneLine,
  formatStreamEventOneLine,
  getEventGroupKey,
  pickLastMeaningfulStreamEvent,
  pickLatestAgentNote,
  pickPrimaryHeadlineEvent,
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
  "chat.stream.thinking": "Working…",
  "chat.stream.warningLine": "W:{{message}}",
  "chat.stream.warningLineWithCode": "W:{{label}}:{{message}}",
  "chat.stream.subagentStarted": "S+{{id}}",
  "chat.stream.subagentStartedDetailed": "S+{{id}}+{{detail}}+{{reason}}",
  "chat.stream.subagentProgress": "P+{{id}}+{{summary}}",
  "chat.stream.subagentFinished": "S-{{id}}",
  "chat.stream.subagentFinishedStateOnly": "S-{{id}}+{{state}}",
  "chat.stream.subagentFinishedDetailed": "S-{{id}}+{{state}}+{{provenance}}",
  "chat.stream.subagentKind.spawned": "spawned",
  "chat.stream.subagentKind.routing": "routing",
  "chat.stream.subagentTerminal.succeeded": "ok",
  "chat.stream.subagentTerminal.failed": "failed",
  "chat.stream.subagentTerminal.cancelled": "cancelled",
  "chat.stream.subagentTerminal.timed_out": "timed_out",
  "chat.stream.answerSynthesisStarted": "SYN+",
  "chat.stream.answerSynthesisFinished": "SYN-",
  "chat.stream.degradedReason.recursion_limit_partial": "DG:recursion",
  "chat.stream.degradedReason.turn_deadline_exceeded": "DG:deadline",
  "chat.stream.finalAnswerEnvelope": "FA-ENV",
  "chat.stream.toolResultLabel": "TR",
  "chat.stream.rowsLabel": "rows",
  "chat.stream.errorLabel": "err",
  "chat.run.live.toolCall": "{{tool}}",
  "chat.run.live.toolCallQuery": "{{tool}}·{{q}}",
  "chat.run.headline.thinkingAbout": "Understanding: {{cls}}…",
  "chat.run.headline.delegatedTo": "Hand off → {{id}}…",
  "chat.run.headline.repeatedSuffix": "{{base}} (×{{count}})",
  "chat.run.live.toolCallRepeated": "TOOL {{base}} ×{{count}}",
  "chat.run.live.productStepRepeated": "STEP {{base}} ×{{count}}",
  "chat.run.decision.label": "Decision",
  "chat.run.decision.why": "Why",
  "chat.run.decision.row": "{{label}}: {{value}}",
  "chat.run.agentNote.label": "Note",
  "chat.stream.agentNote": "Note: {{note}}",
  "chat.run.liveExplain.routeReason": "Routing: {{reason}}",
  "chat.run.liveExplain.intentReason": "Intent {{cls}}: {{reason}}",
  "chat.run.liveExplain.subagentSummary": "Specialist {{id}}: {{summary}}",
  "chat.run.liveExplain.subagentOutcome": "Subtask {{id}} ended with {{state}}; merge provenance: {{provenance}}",
  "chat.run.routeReason.semantic_fast_route": "fast semantic route",
  "chat.run.productStep.searching_literature": "Searching works…",
  "chat.run.productStep.composing_answer": "Composing answer…",
  "chat.run.productStep.using_tool": "Running: {{tool}}…",
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

  it("prefers degraded_mode over answer_synthesis_finished when later in stream", () => {
    const events = [
      { type: "answer_synthesis_finished" },
      { type: "degraded_mode", reasons: ["recursion_limit_partial"] },
    ];
    expect(pickLastMeaningfulStreamEvent(events)?.type).toBe("degraded_mode");
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
    expect(
      formatStreamEventOneLine(t, {
        type: "subagent_started",
        subagent_id: "retrieval_agent",
        kind: "spawned",
        task_type: "corpus_explore",
        spawn_reason: "semantic_fast_route",
      }),
    ).toBe("S+Corpus search+spawned+fast semantic route");
    expect(
      formatStreamEventOneLine(t, { type: "subagent_progress", subagent_id: "r", summary: "search_chunks" }),
    ).toBe("P+R+Search chunks");
    expect(
      formatStreamEventOneLine(t, {
        type: "subagent_finished",
        subagent_id: "r",
        terminal_state: "timed_out",
        merge_provenance: { source_kind: "corpus_explore_result" },
      }),
    ).toBe("S-R+timed_out+corpus_explore_result");
    expect(formatStreamEventOneLine(t, { type: "answer_synthesis_started" })).toBe("SYN+");
    expect(formatStreamEventOneLine(t, { type: "answer_synthesis_finished" })).toBe("SYN-");
    expect(
      formatStreamEventOneLine(t, { type: "degraded_mode", reasons: ["recursion_limit_partial"] }),
    ).toBe("DG:recursion");
    expect(
      formatStreamEventOneLine(t, {
        type: "degraded_mode",
        reasons: ["turn_deadline_exceeded", "recursion_limit_partial"],
      }),
    ).toBe("DG:deadline · DG:recursion");
    expect(formatStreamEventOneLine(t, { type: "degraded_mode", reasons: [] })).toBe("");
  });

  it("formats final_answer SSE envelope without raw type token", () => {
    expect(formatStreamEventOneLine(t, { type: "final_answer", answer: "body" })).toBe("FA-ENV");
  });

  it("hides all tool_search_result variants from headline picker", () => {
    const withRules = [
      { type: "intent_classified", answer_class: "inventory", source: "heuristic" },
      { type: "tool_search_result", specialist: "single_agent_react", reason: "rules" },
    ];
    expect(pickLastMeaningfulStreamEvent(withRules)?.type).toBe("intent_classified");
    const withLowSignal = [
      { type: "intent_classified", answer_class: "inventory", source: "heuristic" },
      { type: "tool_search_result", specialist: "single_agent_react", reason: "low_signal" },
    ];
    expect(pickLastMeaningfulStreamEvent(withLowSignal)?.type).toBe("intent_classified");
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

  it("drops tool_execution and tool_permissions from grouped streams", () => {
    const events = [
      { type: "specialist_selected", from: "sup", to: "ret" },
      { type: "tool_execution", phase: "pre_hooks", ok: true, tools: ["idea_search"] },
      { type: "tool_call", tool: "idea_search" },
      { type: "tool_execution", phase: "post_hooks", ok: true, elapsed_ms: 12 },
      { type: "tool_permissions", matrix: {} },
      { type: "tool_result", tool: "idea_search", row_count: 1 },
    ];
    const g = buildSpecialistStreamGroups(events);
    expect(g.length).toBe(1);
    expect(g[0].events.map((e) => e.type)).toEqual([
      "specialist_selected",
      "tool_call",
      "tool_result",
    ]);
  });

  it("drops final_answer plumbing from grouped streams", () => {
    const events = [
      { type: "specialist_selected", from: "sup", to: "ret" },
      { type: "tool_call", tool: "final_answer" },
      { type: "tool_result", tool: "final_answer", row_count: 3 },
      { type: "subagent_progress", subagent_id: "single_agent_react", tool: "final_answer", summary: "final_answer" },
      { type: "product_step", code: "composing_answer" },
      { type: "final_answer", answer: "text" },
    ];
    const g = buildSpecialistStreamGroups(events);
    expect(g.length).toBe(1);
    expect(g[0].events.map((e) => e.type)).toEqual(["specialist_selected", "product_step"]);
  });
});

describe("collectRecentToolNamesForChips", () => {
  it("skips final_answer tool calls", () => {
    expect(
      collectRecentToolNamesForChips(
        [
          { type: "tool_call", tool: "idea_search" },
          { type: "tool_call", tool: "final_answer" },
        ],
        4,
      ),
    ).toEqual(["idea_search"]);
  });
});

describe("aggregateRepeatedEvents", () => {
  it("collapses 5 adjacent tool_call(idea_search) into one group with count 5", () => {
    const events = [
      { type: "tool_call", tool: "idea_search" },
      { type: "tool_call", tool: "idea_search" },
      { type: "tool_call", tool: "idea_search" },
      { type: "tool_call", tool: "idea_search" },
      { type: "tool_call", tool: "idea_search" },
    ];
    const out = aggregateRepeatedEvents(events);
    expect(out.length).toBe(1);
    expect(out[0].kind).toBe("group");
    expect(out[0].count).toBe(5);
  });

  it("does not merge across a tool_result splitter", () => {
    const events = [
      { type: "tool_call", tool: "idea_search" },
      { type: "tool_call", tool: "idea_search" },
      { type: "tool_result", tool: "idea_search", row_count: 1 },
      { type: "tool_call", tool: "idea_search" },
    ];
    const out = aggregateRepeatedEvents(events);
    expect(out.length).toBe(3);
    expect(out[0].count).toBe(2);
    expect(out[1].kind).toBe("single");
    expect(out[2].count).toBe(1);
  });

  it("does not merge different tools", () => {
    const events = [
      { type: "tool_call", tool: "idea_search" },
      { type: "tool_call", tool: "cypher_query" },
      { type: "tool_call", tool: "idea_search" },
    ];
    const out = aggregateRepeatedEvents(events);
    expect(out.length).toBe(3);
    expect(out.every((e) => e.kind === "single")).toBe(true);
  });

  it("collapses repeated product_step with the same code", () => {
    const events = [
      { type: "product_step", code: "searching_literature" },
      { type: "product_step", code: "searching_literature" },
      { type: "product_step", code: "searching_literature" },
    ];
    const out = aggregateRepeatedEvents(events);
    expect(out.length).toBe(1);
    expect(out[0].count).toBe(3);
  });

  it("uses tool name when grouping using_tool product_step entries", () => {
    expect(getEventGroupKey({ type: "product_step", code: "using_tool", tool: "x" })).toBe(
      "product_step:using_tool:x",
    );
  });
});

describe("formatAggregatedEventOneLine", () => {
  it("appends ×N suffix for groups", () => {
    const entry = {
      kind: "group",
      count: 4,
      event: { type: "tool_call", tool: "idea_search", args_summary: { query: "x" } },
      firstIdx: 0,
      lastIdx: 3,
    };
    const line = formatAggregatedEventOneLine(t, entry);
    expect(line).toContain("×4");
    expect(line.startsWith("TOOL ")).toBe(true);
  });

  it("uses product-step repeat template for product_step groups", () => {
    const entry = {
      kind: "group",
      count: 2,
      event: { type: "product_step", code: "searching_literature" },
      firstIdx: 0,
      lastIdx: 1,
    };
    const line = formatAggregatedEventOneLine(t, entry);
    expect(line).toContain("×2");
    expect(line.startsWith("STEP ")).toBe(true);
  });

  it("returns plain line when count is 1", () => {
    const entry = {
      kind: "single",
      count: 1,
      event: { type: "product_step", code: "searching_literature" },
      firstIdx: 0,
      lastIdx: 0,
    };
    expect(formatAggregatedEventOneLine(t, entry)).toBe("Searching works…");
  });
});

describe("collectFormattedStreamLines aggregation", () => {
  it("collapses adjacent repeats in the recent list", () => {
    const events = Array.from({ length: 6 }, () => ({ type: "tool_call", tool: "idea_search" }));
    const lines = collectFormattedStreamLines(t, events, 24);
    expect(lines.length).toBe(1);
    expect(lines[0]).toContain("×6");
  });
});

describe("derivePrimaryHeadline aggregation", () => {
  it("appends ×N suffix when the trailing primary event repeated", () => {
    const events = [
      { type: "product_step", code: "searching_literature" },
      { type: "product_step", code: "searching_literature" },
      { type: "product_step", code: "searching_literature" },
    ];
    const out = derivePrimaryHeadline(t, events, true);
    expect(out).toContain("Searching works");
    expect(out).toContain("×3");
    expect(out.startsWith("STEP ")).toBe(true);
  });
});

describe("pickPrimaryHeadlineEvent", () => {
  it("prefers product_step over later intent_classified", () => {
    const events = [
      { type: "product_step", code: "searching_literature" },
      { type: "intent_classified", answer_class: "inventory", source: "heuristic" },
    ];
    expect(pickPrimaryHeadlineEvent(events)?.type).toBe("product_step");
  });

  it("prefers product_step over later tool_search_result", () => {
    const events = [
      { type: "product_step", code: "searching_literature" },
      { type: "tool_search_result", specialist: "retrieval_agent", reason: "low_signal" },
    ];
    expect(pickPrimaryHeadlineEvent(events)?.type).toBe("product_step");
  });

  it("falls back to subagent_started when no product_step", () => {
    const events = [
      { type: "intent_classified", answer_class: "x", source: "h" },
      { type: "subagent_started", subagent_id: "retrieval_agent" },
    ];
    expect(pickPrimaryHeadlineEvent(events)?.type).toBe("subagent_started");
  });

  it("returns null when only debug events", () => {
    expect(pickPrimaryHeadlineEvent([{ type: "tool_search_result", specialist: "x", reason: "rules" }])).toBe(null);
  });

  it("picks latest event at same priority level", () => {
    const events = [
      { type: "product_step", code: "searching_literature" },
      { type: "product_step", code: "composing_answer" },
    ];
    expect(pickPrimaryHeadlineEvent(events)?.code).toBe("composing_answer");
  });

  it("ignores stale stamped product_step when the tail event is stamped", () => {
    const t0 = 1_700_000_000_000;
    const events = [
      { type: "product_step", code: "searching_literature", _receivedAtMs: t0 },
      {
        type: "intent_classified",
        answer_class: "inventory",
        source: "heuristic",
        _receivedAtMs: t0 + 9000,
      },
    ];
    expect(pickPrimaryHeadlineEvent(events)?.type).toBe("intent_classified");
  });

  it("keeps fresh stamped product_step over later intent_classified", () => {
    const t0 = 1_700_000_000_000;
    const events = [
      { type: "product_step", code: "searching_literature", _receivedAtMs: t0 },
      {
        type: "intent_classified",
        answer_class: "inventory",
        source: "heuristic",
        _receivedAtMs: t0 + 1000,
      },
    ];
    expect(pickPrimaryHeadlineEvent(events)?.type).toBe("product_step");
  });

  it("prefers degraded_mode over product_step and answer_synthesis_finished", () => {
    const events = [
      { type: "product_step", code: "composing_answer" },
      { type: "answer_synthesis_finished" },
      { type: "degraded_mode", reasons: ["recursion_limit_partial"] },
    ];
    expect(pickPrimaryHeadlineEvent(events)?.type).toBe("degraded_mode");
  });
});

describe("deriveDecisionRationale", () => {
  it("returns localized decision and humanized why", () => {
    const events = [
      { type: "intent_classified", answer_class: "inventory", source: "heuristic", reason: "semantic_fast_route" },
    ];
    const out = deriveDecisionRationale(t, events);
    expect(out.decision).toBe("Inventory list");
    expect(out.why).toBe("fast semantic route");
  });

  it("falls back to specialist_selected reason when intent has none", () => {
    const events = [
      { type: "intent_classified", answer_class: "inventory", source: "heuristic" },
      { type: "specialist_selected", from: "sup", to: "ret", reason: "semantic_fast_route" },
    ];
    const out = deriveDecisionRationale(t, events);
    expect(out.decision).toBe("Inventory list");
    expect(out.why).toBe("fast semantic route");
  });

  it("hides why when reason is the redundant default single_agent_research_runtime", () => {
    const events = [
      { type: "intent_classified", answer_class: "inventory", source: "h", reason: "single_agent_research_runtime" },
    ];
    const out = deriveDecisionRationale(t, events);
    expect(out.decision).toBe("Inventory list");
    expect(out.why).toBe("");
  });

  it("returns empty when no intent or specialist events", () => {
    const out = deriveDecisionRationale(t, [{ type: "tool_call", tool: "x" }]);
    expect(out).toEqual({ decision: "", why: "" });
  });
});

describe("collectSafeExplanationLines with excludeKinds=decision", () => {
  it("skips intent/route reason lines so decision block is not duplicated", () => {
    const events = [
      { type: "intent_classified", answer_class: "inventory", source: "h", reason: "semantic_fast_route" },
      { type: "specialist_selected", from: "sup", to: "ret", reason: "semantic_fast_route" },
      { type: "subagent_started", subagent_id: "retrieval_agent", summary: "semantic_fast_route" },
    ];
    const lines = collectSafeExplanationLines(t, events, 6, { excludeKinds: ["decision"] });
    expect(lines.some((l) => l.startsWith("Routing:"))).toBe(false);
    expect(lines.some((l) => l.startsWith("Intent "))).toBe(false);
    expect(lines.some((l) => l.startsWith("Specialist "))).toBe(true);
  });

  it("includes subagent outcome lines with provenance", () => {
    const lines = collectSafeExplanationLines(t, [
      {
        type: "subagent_finished",
        subagent_id: "retrieval_agent",
        terminal_state: "failed",
        merge_provenance: { source_kind: "corpus_explore_result" },
      },
    ]);
    expect(lines).toContain("Subtask Corpus search ended with failed; merge provenance: corpus_explore_result");
  });
});

describe("buildLiveStatusPresentation", () => {
  it("exposes decision and why fields", () => {
    const events = [
      { type: "intent_classified", answer_class: "inventory", source: "heuristic", reason: "semantic_fast_route" },
    ];
    const pres = buildLiveStatusPresentation(t, events, true);
    expect(pres.decision).toBe("Inventory list");
    expect(pres.why).toBe("fast semantic route");
    expect(pres.headline).toBeTruthy();
  });

  it("exposes latest agent_note text", () => {
    const events = [
      { type: "intent_classified", answer_class: "inventory", source: "heuristic" },
      { type: "agent_note", kind: "intent", note: "Will check authors first." },
      { type: "agent_note", kind: "route", note: "Fetch graph neighbours." },
    ];
    const pres = buildLiveStatusPresentation(t, events, true);
    expect(pres.latestAgentNote).toBe("Fetch graph neighbours.");
  });
});

describe("pickLatestAgentNote", () => {
  it("returns the last non-empty note", () => {
    expect(
      pickLatestAgentNote([
        { type: "agent_note", note: "first" },
        { type: "agent_note", note: "" },
        { type: "agent_note", note: "second" },
      ]),
    ).toBe("second");
  });

  it("returns empty string when no notes are present", () => {
    expect(pickLatestAgentNote([{ type: "tool_call", tool: "x" }])).toBe("");
  });
});

describe("formatStreamEventOneLine agent_note", () => {
  it("formats agent_note with localized template", () => {
    expect(formatStreamEventOneLine(t, { type: "agent_note", kind: "intent", note: "Pick recent papers." })).toBe(
      "Note: Pick recent papers.",
    );
  });

  it("returns empty string when note is blank", () => {
    expect(formatStreamEventOneLine(t, { type: "agent_note", kind: "intent", note: "" })).toBe("");
  });
});

describe("derivePrimaryHeadline", () => {
  it("returns localized product_step phrase", () => {
    const events = [{ type: "product_step", code: "searching_literature" }];
    expect(derivePrimaryHeadline(t, events, true)).toBe("Searching works…");
  });

  it("uses thinkingAbout phrase for early intent_classified", () => {
    const events = [{ type: "intent_classified", answer_class: "inventory", source: "heuristic" }];
    expect(derivePrimaryHeadline(t, events, true)).toBe("Understanding: Inventory list…");
  });

  it("uses delegatedTo phrase for subagent_started", () => {
    const events = [{ type: "subagent_started", subagent_id: "retrieval_agent" }];
    expect(derivePrimaryHeadline(t, events, true)).toBe("Hand off → Corpus search…");
  });

  it("falls back to chat.stream.thinking when only hidden events on active run", () => {
    const events = [{ type: "tool_search_result", specialist: "x", reason: "rules" }];
    expect(derivePrimaryHeadline(t, events, true)).toBe("Working…");
  });

  it("returns empty when not active and no events", () => {
    expect(derivePrimaryHeadline(t, [], false)).toBe("");
  });

  it("never returns raw using_tool without a label", () => {
    const events = [{ type: "product_step", code: "using_tool", tool: "idea_search" }];
    const out = derivePrimaryHeadline(t, events, true);
    expect(out).not.toBe("using_tool");
    expect(out).toContain("Running");
  });
});
