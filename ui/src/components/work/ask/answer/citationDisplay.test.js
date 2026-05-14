/** @vitest-environment node */
import { describe, expect, it } from "vitest";

import {
  citationNumericScore,
  formatCitationHeadline,
  formatCitationWorkLabel,
  isWorkOnlyCitation,
  pickCitationWorkTitle,
} from "./citationDisplay.js";

function t(key, vars = {}) {
  if (key === "askPanel.citation.rankLabel") return `Цитата #${vars.rank}`;
  if (key === "askPanel.citation.workRankLabel") return `Статья #${vars.rank}`;
  return key;
}

describe("citationDisplay", () => {
  it("formats headline without score when missing", () => {
    const headline = formatCitationHeadline({
      rank: "2",
      citation: { work_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" },
      chatDetailLevel: "simple",
      t,
    });
    expect(headline).toContain("Статья #2");
    expect(headline).not.toContain("score");
    expect(headline).not.toMatch(/aaaaaaaa/);
  });

  it("includes numeric score when present", () => {
    const headline = formatCitationHeadline({
      rank: "1",
      citation: { work_id: "w1", score: 0.91 },
      chatDetailLevel: "simple",
      t,
    });
    expect(headline).toContain("0.91");
  });

  it("classifies only work references without passage or chunk as work-only", () => {
    expect(isWorkOnlyCitation({ work_id: "w1", title: "Paper" })).toBe(true);
    expect(isWorkOnlyCitation({ work_id: "w1", excerpt: "Passage" })).toBe(false);
    expect(isWorkOnlyCitation({ work_id: "w1", chunk_fingerprint: "fp1" })).toBe(false);
  });

  it("prefers title over work_id in label", () => {
    expect(
      formatCitationWorkLabel({ work_id: "uuid", title: "Paper" }, "simple"),
    ).toBe("Paper");
    expect(pickCitationWorkTitle({ paper_title: " P " })).toBe("P");
  });

  it("work-only list mode omits truncated work_id from work label", () => {
    expect(formatCitationWorkLabel({ work_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" }, "simple", { workOnlyListMode: true })).toBe(
      "",
    );
    expect(formatCitationWorkLabel({ work_id: "w1", title: "T" }, "simple", { workOnlyListMode: true })).toBe("T");
  });

  it("parses citationNumericScore", () => {
    expect(citationNumericScore({ similarity: "0.5" })).toBe(0.5);
    expect(citationNumericScore({ score: null })).toBe(null);
  });
});
