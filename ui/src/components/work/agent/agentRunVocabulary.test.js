/** @vitest-environment node */
import { describe, expect, it } from "vitest";

import {
  __VOCAB_KEYS,
  humanizeUnknownCode,
  isRedundantIntentSource,
  mapAnswerClassToLabel,
  mapErrorCodeToLabel,
  mapIntentSourceToLabel,
  mapRouteReasonToLabel,
  mapSpecialistToLabel,
  mapToolSearchReasonToLabel,
  shouldHideStreamEventFromHeadline,
} from "./agentRunVocabulary.js";
import enMessages from "../../../i18n/messages/en/partChat.js";
import ruMessages from "../../../i18n/messages/ru/partChat.js";

function makeT(table) {
  return (key, vars = {}) => {
    if (!Object.prototype.hasOwnProperty.call(table, key)) return key;
    let out = table[key];
    Object.entries(vars).forEach(([k, v]) => {
      out = out.split(`{{${k}}}`).join(String(v));
    });
    return out;
  };
}

const tEn = makeT(enMessages);
const tRu = makeT(ruMessages);

describe("humanizeUnknownCode", () => {
  it("turns snake_case into a sentence with leading capital", () => {
    expect(humanizeUnknownCode("single_agent_research_runtime")).toBe("Single agent research runtime");
  });

  it("normalizes mixed separators", () => {
    expect(humanizeUnknownCode("foo.bar-baz")).toBe("Foo bar baz");
  });

  it("returns empty string for empty / nullish input", () => {
    expect(humanizeUnknownCode("")).toBe("");
    expect(humanizeUnknownCode(null)).toBe("");
    expect(humanizeUnknownCode(undefined)).toBe("");
  });
});

describe("vocabulary i18n coverage", () => {
  it("EN has a translation for every known specialist", () => {
    for (const key of __VOCAB_KEYS.SPECIALIST_KEYS) {
      expect(enMessages[`chat.run.specialist.${key}`], `EN missing ${key}`).toBeTruthy();
      expect(ruMessages[`chat.run.specialist.${key}`], `RU missing ${key}`).toBeTruthy();
    }
  });

  it("EN has a translation for every known answer_class", () => {
    for (const key of __VOCAB_KEYS.ANSWER_CLASS_KEYS) {
      expect(enMessages[`chat.run.answerClass.${key}`], `EN missing ${key}`).toBeTruthy();
      expect(ruMessages[`chat.run.answerClass.${key}`], `RU missing ${key}`).toBeTruthy();
    }
  });

  it("EN has a translation for every known tool_search reason", () => {
    for (const key of __VOCAB_KEYS.TOOL_SEARCH_REASON_KEYS) {
      expect(enMessages[`chat.run.toolSearchReason.${key}`], `EN missing ${key}`).toBeTruthy();
      expect(ruMessages[`chat.run.toolSearchReason.${key}`], `RU missing ${key}`).toBeTruthy();
    }
  });

  it("EN has a translation for every known route reason", () => {
    for (const key of __VOCAB_KEYS.ROUTE_REASON_KEYS) {
      expect(enMessages[`chat.run.routeReason.${key}`], `EN missing ${key}`).toBeTruthy();
      expect(ruMessages[`chat.run.routeReason.${key}`], `RU missing ${key}`).toBeTruthy();
    }
  });

  it("EN has a translation for every known intent source", () => {
    for (const key of __VOCAB_KEYS.INTENT_SOURCE_KEYS) {
      expect(enMessages[`chat.run.intentSource.${key}`], `EN missing ${key}`).toBeTruthy();
      expect(ruMessages[`chat.run.intentSource.${key}`], `RU missing ${key}`).toBeTruthy();
    }
  });
});

describe("mappers translate known codes", () => {
  it("mapSpecialistToLabel returns localized label", () => {
    expect(mapSpecialistToLabel(tEn, "single_agent_react")).toBe("Research agent");
    expect(mapSpecialistToLabel(tRu, "single_agent_react")).toBe("Исследовательский агент");
    expect(mapSpecialistToLabel(tEn, "retrieval_agent")).toBe("Corpus search");
  });

  it("mapAnswerClassToLabel returns localized label", () => {
    expect(mapAnswerClassToLabel(tEn, "grounded_explanation")).toBe("Explanation with citations");
    expect(mapAnswerClassToLabel(tRu, "grounded_explanation")).toBe("Объяснение со ссылками");
  });

  it("mapToolSearchReasonToLabel collapses fallback variants", () => {
    expect(mapToolSearchReasonToLabel(tEn, "low_signal")).toBe("full toolset");
    expect(mapToolSearchReasonToLabel(tEn, "fallback_full")).toBe("full toolset");
    expect(mapToolSearchReasonToLabel(tEn, "fallback_full_single_agent")).toBe("full toolset");
  });

  it("mapRouteReasonToLabel returns localized label", () => {
    expect(mapRouteReasonToLabel(tRu, "budget_exhausted")).toBe("исчерпан бюджет хода");
  });

  it("mapIntentSourceToLabel hides redundant defaults", () => {
    expect(mapIntentSourceToLabel(tEn, "single_agent_research_v1")).toBe("");
    expect(mapIntentSourceToLabel(tEn, "coordinator_gate_v0")).toBe("");
    expect(mapIntentSourceToLabel(tEn, "heuristic")).toBe("heuristic");
  });
});

describe("mappers fall back on unknown codes", () => {
  it("mapSpecialistToLabel falls back via humanizeUnknownCode", () => {
    expect(mapSpecialistToLabel(tEn, "future_specialist_v9")).toBe("Future specialist v9");
  });

  it("mapAnswerClassToLabel falls back via humanizeUnknownCode", () => {
    expect(mapAnswerClassToLabel(tEn, "unknown_class")).toBe("Unknown class");
  });

  it("mapErrorCodeToLabel falls back via humanizeUnknownCode", () => {
    expect(mapErrorCodeToLabel(tEn, "weird_error")).toBe("Weird error");
  });
});

describe("isRedundantIntentSource", () => {
  it("flags single_agent_research_v1 and coordinator_gate_v0", () => {
    expect(isRedundantIntentSource("single_agent_research_v1")).toBe(true);
    expect(isRedundantIntentSource("coordinator_gate_v0")).toBe(true);
    expect(isRedundantIntentSource("heuristic")).toBe(false);
  });
});

describe("shouldHideStreamEventFromHeadline", () => {
  it("hides tool_search_result with reason=rules", () => {
    expect(
      shouldHideStreamEventFromHeadline({ type: "tool_search_result", reason: "rules", specialist: "single_agent_react" }),
    ).toBe(true);
  });

  it("does not hide tool_search_result with low_signal", () => {
    expect(
      shouldHideStreamEventFromHeadline({ type: "tool_search_result", reason: "low_signal", specialist: "x" }),
    ).toBe(false);
  });

  it("does not hide unrelated event types", () => {
    expect(shouldHideStreamEventFromHeadline({ type: "intent_classified" })).toBe(false);
    expect(shouldHideStreamEventFromHeadline(null)).toBe(false);
  });
});
