import { describe, expect, it, vi } from "vitest";

import { flushAgentSseEventBuffer, parseAgentSseJson } from "./agentStreamParse.js";

describe("parseAgentSseJson", () => {
  it("parses valid JSON", () => {
    expect(parseAgentSseJson('{"type":"tool_call","step":1}')).toEqual({ type: "tool_call", step: 1 });
  });

  it("returns null and notifies on invalid JSON", () => {
    const onParseError = vi.fn();
    expect(parseAgentSseJson("{not-json", { onParseError })).toBeNull();
    expect(onParseError).toHaveBeenCalled();
  });

  it("joins multi-line data payload before parse", () => {
    const raw = '{"a":1}\n{"b":2}';
    const onParseError = vi.fn();
    expect(parseAgentSseJson(raw, { onParseError })).toBeNull();
    expect(onParseError).toHaveBeenCalled();
  });

  it("parses final_answer shaped payload", () => {
    const ev = parseAgentSseJson('{"type":"final_answer","answer":"x","citations":[],"tool_trace":[]}');
    expect(ev?.type).toBe("final_answer");
    expect(ev?.answer).toBe("x");
  });
});

describe("flushAgentSseEventBuffer", () => {
  it("joins multiple data lines into one JSON object", () => {
    const onEvent = vi.fn();
    const frame =
      'data: {"type":"intent_classified",\n' +
      'data: "answer_class":"inventory","source":"heuristic"}\n\n';
    flushAgentSseEventBuffer(frame, { onEvent });
    expect(onEvent).toHaveBeenCalledTimes(1);
    expect(onEvent.mock.calls[0][0]).toMatchObject({
      type: "intent_classified",
      answer_class: "inventory",
      source: "heuristic",
    });
  });

  it("emits events for complete frames and keeps trailing partial", () => {
    const onEvent = vi.fn();
    const onFinalAnswer = vi.fn();
    const onError = vi.fn();
    const rest = flushAgentSseEventBuffer('data: {"type":"intent_classified","answer_class":"x"}\n\ndata: {', {
      onEvent,
      onFinalAnswer,
      onError,
    });
    expect(onEvent).toHaveBeenCalledTimes(1);
    expect(onEvent.mock.calls[0][0].type).toBe("intent_classified");
    expect(rest).toBe("data: {");
  });

  it("routes final_answer and error", () => {
    const onFinalAnswer = vi.fn();
    const onError = vi.fn();
    flushAgentSseEventBuffer('data: {"type":"final_answer","answer":"ok"}\n\n', { onFinalAnswer, onError });
    expect(onFinalAnswer).toHaveBeenCalledWith(expect.objectContaining({ type: "final_answer" }));

    flushAgentSseEventBuffer('data: {"type":"error","detail":"boom"}\n\n', { onError });
    expect(onError).toHaveBeenCalledWith("boom");
  });

  it("parses sse_starlette CRLF frame delimiters", () => {
    const onEvent = vi.fn();
    const onFinalAnswer = vi.fn();
    const crlfFrame =
      'data: {"type":"intent_classified","answer_class":"x","source":"heuristic"}\r\n\r\n' +
      'data: {"type":"final_answer","answer":"hi","citations":[],"tool_trace":[]}\r\n\r\n';
    const rest = flushAgentSseEventBuffer(`${crlfFrame}data: {`, { onEvent, onFinalAnswer });
    expect(onEvent).toHaveBeenCalledTimes(2);
    expect(onFinalAnswer).toHaveBeenCalledTimes(1);
    expect(onFinalAnswer).toHaveBeenCalledWith(expect.objectContaining({ type: "final_answer", answer: "hi" }));
    expect(rest).toBe("data: {");
  });
});
