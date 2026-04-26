import { describe, expect, it } from "vitest";

import { buildTrustRows, decisionChipSx } from "./TrustSignalPanel.jsx";

describe("TrustSignalPanel re-exports", () => {
  it("buildTrustRows is available from panel entry", () => {
    expect(buildTrustRows(null)).toEqual([]);
  });

  it("decisionChipSx marks NO-GO", () => {
    const sx = decisionChipSx("NO-GO");
    expect(sx.color).toContain("239");
  });
});
