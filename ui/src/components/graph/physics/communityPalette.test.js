import { describe, expect, it } from "vitest";

import {
  buildCommunityColorStyleMap,
  COMMUNITY_PALETTE_RANK_SLOTS,
  neutralCommunityColors,
  rankedCommunityPalette,
  sortedCommunitiesByCount,
} from "./communityPalette.js";

describe("rankedCommunityPalette", () => {
  it("returns distinct hues for ranks 0 and 1", () => {
    const a = rankedCommunityPalette(0, "dark");
    const b = rankedCommunityPalette(1, "dark");
    expect(a.fill).not.toBe(b.fill);
  });

  it("differs between light and dark for the same rank", () => {
    const d = rankedCommunityPalette(2, "dark");
    const l = rankedCommunityPalette(2, "light");
    expect(d.fill).not.toBe(l.fill);
  });

  it("uses neutral palette beyond rank slots", () => {
    const o = rankedCommunityPalette(COMMUNITY_PALETTE_RANK_SLOTS, "dark");
    const n = neutralCommunityColors("dark");
    expect(o.fill).toBe(n.fill);
  });
});

describe("sortedCommunitiesByCount", () => {
  it("sorts by descending count then id", () => {
    const m = new Map([
      ["b", "big"],
      ["a", "big"],
      ["c", "small"],
    ]);
    const rows = sortedCommunitiesByCount(m);
    expect(rows.map((r) => r.id)).toEqual(["big", "small"]);
    expect(rows[0].count).toBe(2);
    expect(rows[1].count).toBe(1);
  });
});

describe("buildCommunityColorStyleMap", () => {
  it("assigns monotonically increasing rank per sorted community", () => {
    const m = new Map([
      ["n1", "c2"],
      ["n2", "c2"],
      ["n3", "c1"],
    ]);
    const styles = buildCommunityColorStyleMap(m, "dark");
    expect(styles.get("c2")?.rank).toBe(0);
    expect(styles.get("c1")?.rank).toBe(1);
  });
});
