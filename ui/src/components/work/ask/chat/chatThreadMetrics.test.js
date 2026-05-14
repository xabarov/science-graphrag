/** @vitest-environment node */
import { describe, expect, it } from "vitest";

import { estimateCostUsdFromOpenrouterReference } from "./chatThreadMetrics.js";

describe("estimateCostUsdFromOpenrouterReference", () => {
  it("returns null without pricing block", () => {
    expect(estimateCostUsdFromOpenrouterReference({}, 100, 50)).toBeNull();
  });

  it("uses single-model rates when only chat is present", () => {
    const runMeta = {
      openrouter_reference_pricing_usd_per_1m: {
        chat: { model_id: "a/b", prompt_usd_per_1m: 1, completion_usd_per_1m: 2 },
      },
    };
    // 100 prompt + 50 completion tokens → 100/1e6 * 1 + 50/1e6 * 2 = 0.0002
    expect(estimateCostUsdFromOpenrouterReference(runMeta, 100, 50)).toBeCloseTo(0.0002, 10);
  });

  it("averages chat and extraction rates when both are present", () => {
    const runMeta = {
      openrouter_reference_pricing_usd_per_1m: {
        chat: { model_id: "a/b", prompt_usd_per_1m: 0.071, completion_usd_per_1m: 0.1 },
        extraction: { model_id: "c/d", prompt_usd_per_1m: 0.075, completion_usd_per_1m: 0.2 },
      },
    };
    const est = estimateCostUsdFromOpenrouterReference(runMeta, 1_000_000, 1_000_000);
    const avgPrompt = (0.071 + 0.075) / 2;
    const avgComp = (0.1 + 0.2) / 2;
    expect(est).toBeCloseTo(avgPrompt + avgComp, 10);
  });
});
