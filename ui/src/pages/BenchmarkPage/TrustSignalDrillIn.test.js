import React from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import TrustSignalDrillIn from "./TrustSignalDrillIn.jsx";

const t = (key) => key;

describe("TrustSignalDrillIn", () => {
  it("renders nothing when nothing to show", () => {
    const html = renderToString(
      React.createElement(TrustSignalDrillIn, { criteria: {}, trustByFamily: {}, t }),
    );
    expect(html).toBe("");
  });

  it("includes warnings, validation, and advisory failure markers", () => {
    const html = renderToString(
      React.createElement(TrustSignalDrillIn, {
        t,
        criteria: {
          advisory_individual_failures: [
            { family: "retrieval_family", member_id: "m1", case_id: "case_a", metrics: { passed: false } },
          ],
        },
        trustByFamily: {
          retrieval_family: {
            members: {
              m1: {
                consistency_warnings: ["orphan warning"],
                validation_status_aggregate: "draft",
              },
            },
          },
        },
      }),
    );
    expect(html).toContain("retrieval_family.m1: orphan warning");
    expect(html).toContain("draft");
    expect(html).toContain("case_a");
    expect(html).toContain("retrieval_family.m1");
  });
});
