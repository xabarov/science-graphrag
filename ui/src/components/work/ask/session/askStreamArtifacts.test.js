import { describe, expect, it } from "vitest";

import { extractOpenStructuredQuestion, extractResearchPlanStreamHint } from "./askStreamArtifacts.js";

describe("askStreamArtifacts", () => {
  it("extractOpenStructuredQuestion keeps last unanswered ask", () => {
    const ev = [
      { type: "intent_classified" },
      {
        type: "user_question_asked",
        request_id: "r1",
        questions: [{ id: "q1", prompt: "P", options: [{ id: "a", label: "A" }, { id: "b", label: "B" }] }],
      },
    ];
    const o = extractOpenStructuredQuestion(ev);
    expect(o?.request_id).toBe("r1");
    expect(Array.isArray(o?.questions)).toBe(true);
  });

  it("extractOpenStructuredQuestion clears after user_answered", () => {
    const ev = [
      {
        type: "user_question_asked",
        request_id: "r1",
        questions: [{ id: "q1", prompt: "P", options: [{ id: "a", label: "A" }, { id: "b", label: "B" }] }],
      },
      { type: "user_answered", request_id: "r1", answer_count: 1 },
    ];
    expect(extractOpenStructuredQuestion(ev)).toBeNull();
  });

  it("extractResearchPlanStreamHint returns last hint", () => {
    const h = extractResearchPlanStreamHint([
      { type: "research_plan_updated", item_count: 2 },
      { type: "research_plan_updated", item_count: 5 },
    ]);
    expect(h?.item_count).toBe(5);
  });
});
