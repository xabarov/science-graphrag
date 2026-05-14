/** @vitest-environment node */
import { describe, expect, it } from "vitest";

import {
  citationNumericScore,
  formatCitationHeadline,
  isWorkOnlyCitation,
  pickCitationWorkTitle,
} from "./citationDisplay.js";

function t(key, vars = {}) {
  if (key === "askPanel.citation.rankLabel") return `Цитата #${vars.rank}`;
  if (key === "askPanel.citation.workRankLabel") return `Статья #${vars.rank}`;
  return key;
}

describe("citationDisplay", () => {
  it("formats work-only headline without work_id or score in simple mode", () => {
    const headline = formatCitationHeadline({
      rank: "2",
      citation: { work_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" },
      chatDetailLevel: "simple",
      t,
    });
    expect(headline).toBe("Статья #2");
  });

  it("includes numeric score only in detailed mode", () => {
    const simple = formatCitationHeadline({
      rank: "1",
      citation: { work_id: "w1", score: 0.91, excerpt: "x" },
      chatDetailLevel: "simple",
      t,
    });
    expect(simple).toBe("Цитата #1");
    const detailed = formatCitationHeadline({
      rank: "1",
      citation: { work_id: "w1", score: 0.91, excerpt: "x" },
      chatDetailLevel: "detailed",
      t,
    });
    expect(detailed).toContain("0.91");
    expect(detailed).toContain("Цитата #1");
  });

  it("classifies only work references without passage or chunk as work-only", () => {
    expect(isWorkOnlyCitation({ work_id: "w1", title: "Paper" })).toBe(true);
    expect(isWorkOnlyCitation({ work_id: "w1", excerpt: "Passage" })).toBe(false);
    expect(isWorkOnlyCitation({ work_id: "w1", chunk_fingerprint: "fp1" })).toBe(false);
  });

  it("prefers title over work_id in label", () => {
    const headline = formatCitationHeadline({
      rank: "3",
      citation: { work_id: "uuid", title: "Paper", excerpt: "Body" },
      chatDetailLevel: "simple",
      t,
    });
    expect(headline).toBe("Цитата #3");
    expect(pickCitationWorkTitle({ paper_title: " P " })).toBe("P");
  });

  it("never includes work_id in headline, regardless of detail level", () => {
    const simple = formatCitationHeadline({
      rank: "1",
      citation: { work_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", excerpt: "Body" },
      chatDetailLevel: "simple",
      t,
    });
    const detailed = formatCitationHeadline({
      rank: "1",
      citation: { work_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", excerpt: "Body", score: 0.99 },
      chatDetailLevel: "detailed",
      t,
    });
    expect(simple).toBe("Цитата #1");
    expect(detailed).toContain("Цитата #1");
    expect(simple).not.toMatch(/aaaaaaaa/);
    expect(detailed).not.toMatch(/aaaaaaaa/);
  });

  it("parses citationNumericScore", () => {
    expect(citationNumericScore({ similarity: "0.5" })).toBe(0.5);
    expect(citationNumericScore({ score: null })).toBe(null);
  });
});
