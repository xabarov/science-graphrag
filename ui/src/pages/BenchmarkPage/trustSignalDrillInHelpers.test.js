import { describe, expect, it } from "vitest";

import {
  buildTrustRows,
  collectAdvisoryFailureRows,
  collectConsistencyWarningLines,
  collectValidationStatusRows,
  decisionChipSx,
  decisionChipSxDemoted,
} from "./trustSignalDrillInHelpers.js";

describe("trustSignalDrillInHelpers", () => {
  it("buildTrustRows handles empty input", () => {
    expect(buildTrustRows(null)).toEqual([]);
    expect(buildTrustRows({})).toEqual([]);
  });

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

  it("collectConsistencyWarningLines prefixes when needed", () => {
    const lines = collectConsistencyWarningLines({
      retrieval_family: {
        members: {
          merge_safe: {
            consistency_warnings: [
              "merge_safe: already has member prefix",
              "needs prefix",
            ],
          },
        },
      },
    });
    expect(lines).toContain("merge_safe: already has member prefix");
    expect(lines).toContain("retrieval_family.merge_safe: needs prefix");
  });

  it("collectValidationStatusRows skips null aggregate", () => {
    expect(
      collectValidationStatusRows({
        f: {
          members: {
            m1: { validation_status_aggregate: null },
            m2: { validation_status_aggregate: "draft" },
            m3: { validation_status_aggregate: "   " },
          },
        },
      }),
    ).toEqual([{ familyKey: "f", memberId: "m2", aggregate: "draft" }]);
  });

  it("collectAdvisoryFailureRows maps case and passed", () => {
    const rows = collectAdvisoryFailureRows({
      advisory_individual_failures: [
        { family: "retrieval_family", member_id: "live", case_id: "c1", metrics: { passed: false } },
        "skip",
        {},
      ],
    });
    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({
      family: "retrieval_family",
      memberId: "live",
      caseId: "c1",
      passed: false,
    });
  });

  it("decisionChipSx marks NO-GO", () => {
    const sx = decisionChipSx("NO-GO");
    expect(sx.color).toContain("239");
  });

  it("decisionChipSx marks GO", () => {
    const sx = decisionChipSx("GO");
    expect(sx.color).toContain("129");
  });

  it("decisionChipSxDemoted uses lighter emphasis than decisionChipSx", () => {
    const dem = decisionChipSxDemoted("NO-GO");
    const hero = decisionChipSx("NO-GO");
    expect(dem.fontWeight).toBeLessThan(hero.fontWeight);
  });
});
