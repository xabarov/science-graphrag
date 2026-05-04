import { describe, expect, it } from "vitest";

import {
  buildCombinedMarkdownFromChunks,
  buildReaderSectionPathList,
  isChunkFocused,
  sortChunksByOrder,
  truncateWithEllipsis,
} from "./readerFormatters.js";

describe("buildReaderSectionPathList", () => {
  it("returns unique section paths in order", () => {
    expect(
      buildReaderSectionPathList([
        { section_path: "Intro" },
        { section_path: "Methods" },
        { section_path: "Intro" },
      ]),
    ).toEqual(["Intro", "Methods"]);
  });
});

describe("sortChunksByOrder", () => {
  it("returns empty array for non-array input", () => {
    expect(sortChunksByOrder(null)).toEqual([]);
    expect(sortChunksByOrder(undefined)).toEqual([]);
    expect(sortChunksByOrder({})).toEqual([]);
  });

  it("sorts by order with missing order treated as 0", () => {
    const a = { order: 2, text: "b" };
    const b = { order: undefined, text: "a" };
    const c = { order: 1, text: "c" };
    expect(sortChunksByOrder([a, b, c]).map((x) => x.text)).toEqual(["a", "c", "b"]);
  });

  it("does not mutate original array", () => {
    const items = [{ order: 2 }, { order: 1 }];
    const orig0 = items[0];
    sortChunksByOrder(items);
    expect(items[0]).toBe(orig0);
  });
});

describe("buildCombinedMarkdownFromChunks", () => {
  it("returns empty string for empty or invalid input", () => {
    expect(buildCombinedMarkdownFromChunks([])).toBe("");
    expect(buildCombinedMarkdownFromChunks(null)).toBe("");
    expect(buildCombinedMarkdownFromChunks(undefined)).toBe("");
  });

  it("joins sections with path header and separator", () => {
    const items = [
      { order: 0, section_path: "Intro", text: "Hello" },
      { order: 1, section_path: "Methods", text: "Do X" },
    ];
    expect(buildCombinedMarkdownFromChunks(items)).toBe(
      "## Intro\n\nHello\n\n---\n\n## Methods\n\nDo X",
    );
  });

  it("skips empty trimmed chunks in output", () => {
    const items = [
      { order: 0, text: "   " },
      { order: 1, text: "Real" },
    ];
    expect(buildCombinedMarkdownFromChunks(items)).toBe("Real");
  });

  it("strips leaked whole-document markdown fences at chunk edges", () => {
    const items = [
      { order: 0, section_path: "(preamble)", text: "```markdown\n# Title\n\nIntro" },
      { order: 1, section_path: "Body", text: "More text\n```" },
    ];
    expect(buildCombinedMarkdownFromChunks(items)).toBe(
      "## (preamble)\n\n# Title\n\nIntro\n\n---\n\n## Body\n\nMore text",
    );
  });
});

describe("truncateWithEllipsis", () => {
  it("handles null and non-string", () => {
    expect(truncateWithEllipsis(null, 10)).toEqual({ text: "", truncated: false });
    expect(truncateWithEllipsis(undefined, 10)).toEqual({ text: "", truncated: false });
    expect(truncateWithEllipsis(123, 10)).toEqual({ text: "", truncated: false });
  });

  it("maxLen <= 0 returns full string without marking truncated", () => {
    expect(truncateWithEllipsis("abc", 0)).toEqual({ text: "abc", truncated: false });
    expect(truncateWithEllipsis("abc", -1)).toEqual({ text: "abc", truncated: false });
  });

  it("does not truncate when length equals maxLen", () => {
    expect(truncateWithEllipsis("abcd", 4)).toEqual({ text: "abcd", truncated: false });
  });

  it("truncates when length exceeds maxLen", () => {
    expect(truncateWithEllipsis("abcdef", 4)).toEqual({ text: "abcd…", truncated: true });
  });

  it("handles empty string", () => {
    expect(truncateWithEllipsis("", 5)).toEqual({ text: "", truncated: false });
  });

  it("handles very long single-line string", () => {
    const s = "x".repeat(10000);
    const { text, truncated } = truncateWithEllipsis(s, 100);
    expect(truncated).toBe(true);
    expect(text.length).toBe(101);
    expect(text.endsWith("…")).toBe(true);
  });
});

describe("isChunkFocused", () => {
  const chunk = { chunk_fingerprint: "fp1", section_path: "sec.A" };

  it("returns false when no focus", () => {
    expect(isChunkFocused(chunk, {})).toBe(false);
    expect(isChunkFocused(chunk, { focusedFingerprint: "", focusedSection: "" })).toBe(false);
  });

  it("matches fingerprint when focus set", () => {
    expect(isChunkFocused(chunk, { focusedFingerprint: "fp1" })).toBe(true);
    expect(isChunkFocused(chunk, { focusedFingerprint: "fp2" })).toBe(false);
  });

  it("matches section when focus set", () => {
    expect(isChunkFocused(chunk, { focusedSection: "sec.A" })).toBe(true);
    expect(isChunkFocused(chunk, { focusedSection: "sec.B" })).toBe(false);
  });

  it("empty focus strings do not match empty chunk fields as positive", () => {
    const emptyFp = { chunk_fingerprint: "", section_path: "p" };
    expect(isChunkFocused(emptyFp, { focusedFingerprint: "", focusedSection: "p" })).toBe(true);
  });
});
