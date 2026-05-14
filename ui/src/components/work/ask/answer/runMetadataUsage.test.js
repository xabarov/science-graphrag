/** @vitest-environment node */
import { describe, expect, it } from "vitest";

import { extractTokenCountsFromRunMetadata } from "./runMetadataUsage.js";

describe("extractTokenCountsFromRunMetadata", () => {
  it("reads nested usage object", () => {
    const out = extractTokenCountsFromRunMetadata({
      usage: { prompt_tokens: 10, completion_tokens: 3, total_tokens: 13 },
    });
    expect(out.promptTokens).toBe(10);
    expect(out.completionTokens).toBe(3);
    expect(out.totalTokens).toBe(13);
  });

  it("sums prompt and completion into total when total missing", () => {
    const out = extractTokenCountsFromRunMetadata({
      usage: { input_tokens: 5, output_tokens: 7 },
    });
    expect(out.totalTokens).toBe(12);
  });
});
