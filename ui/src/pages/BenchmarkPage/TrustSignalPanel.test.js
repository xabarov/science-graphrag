import { describe, expect, it } from "vitest";

import { buildTrustRows, decisionChipSx } from "./TrustSignalPanel.jsx";

describe("TrustSignalPanel helpers", () => {
  it("buildTrustRows flattens members", () => {
    const rows = buildTrustRows({
      retrieval_family: {
        members: {
          a: { runtime_mode: "canned", is_phantom: true },
          b: { runtime_mode: "live", is_phantom: false },
        },
      },
    });
    expect(rows).toHaveLength(2);
    expect(rows.filter((r) => r.isPhantom)).toHaveLength(1);
  });

  it("buildTrustRows handles empty input", () => {
    expect(buildTrustRows(null)).toEqual([]);
    expect(buildTrustRows({})).toEqual([]);
  });

  it("decisionChipSx marks NO-GO", () => {
    const sx = decisionChipSx("NO-GO");
    expect(sx.color).toContain("239");
  });

  it("decisionChipSx marks GO", () => {
    const sx = decisionChipSx("GO");
    expect(sx.color).toContain("129");
  });
});
