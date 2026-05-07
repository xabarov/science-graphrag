import { describe, expect, it } from "vitest";

import { apiSessionsToBundle, compactAskTurnDetailsForSync, entriesToApiTurns } from "./askSessionServerBridge.js";

describe("askSessionServerBridge details sync", () => {
  it("round-trips brief and open_structured_question through API turn mapping", () => {
    const bundle = apiSessionsToBundle({
      sessions: [
        {
          id: "sess-1",
          title: "T",
          updated_at: "2026-01-01T00:00:00Z",
          turns: [
            {
              query: "q1",
              workId: "",
              topK: 5,
              answer: "a1",
              citationCount: 0,
              mode: "global",
              savedAt: "2026-01-01T00:00:01Z",
              details: {
                run_metadata: { brief: "Short brief", research_plan: { items: [{ id: "1", content: "x", status: "pending" }] } },
                open_structured_question: {
                  request_id: "r1",
                  questions: [{ id: "q1", prompt: "Pick", options: [{ id: "a", label: "A" }, { id: "b", label: "B" }] }],
                },
                stream_events: [{ type: "user_question_asked", request_id: "r1", questions: [] }],
              },
            },
          ],
        },
      ],
      active_session_id: "sess-1",
    });
    const s0 = bundle.sessions[0];
    expect(s0.entries[0].details?.run_metadata?.brief).toBe("Short brief");
    expect(s0.entries[0].details?.open_structured_question?.request_id).toBe("r1");
  });

  it("entriesToApiTurns uses compact details payload", () => {
    const rows = entriesToApiTurns([
      {
        query: "q",
        workId: "",
        topK: 5,
        answer: "a",
        citationCount: 0,
        mode: "global",
        savedAt: "t",
        details: {
          run_metadata: { brief: "b", noise: "drop-me" },
          open_structured_question: { request_id: "x", questions: [] },
          stream_events: new Array(40).fill({ type: "noop" }),
        },
      },
    ]);
    expect(rows[0].details).toBeDefined();
    expect(rows[0].details.run_metadata?.noise).toBeUndefined();
    expect(rows[0].details.open_structured_question).toBeUndefined();
    expect(Array.isArray(rows[0].details.stream_events)).toBe(true);
    expect(rows[0].details.stream_events.length).toBeLessThanOrEqual(30);
  });

  it("entriesToApiTurns keeps open_structured_question when questions are non-empty", () => {
    const rows = entriesToApiTurns([
      {
        query: "q",
        workId: "",
        topK: 5,
        answer: "a",
        citationCount: 0,
        mode: "global",
        savedAt: "t",
        details: {
          open_structured_question: {
            request_id: "rid",
            questions: [
              {
                id: "q1",
                prompt: "Pick",
                options: [
                  { id: "a", label: "A" },
                  { id: "b", label: "B" },
                ],
              },
            ],
          },
        },
      },
    ]);
    expect(rows[0].details?.open_structured_question?.request_id).toBe("rid");
  });

  it("compactAskTurnDetailsForSync returns undefined for empty details", () => {
    expect(compactAskTurnDetailsForSync(null)).toBeUndefined();
    expect(compactAskTurnDetailsForSync({})).toBeUndefined();
  });
});
