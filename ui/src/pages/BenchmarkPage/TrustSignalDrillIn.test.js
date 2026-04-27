import React from "react";
import { ThemeProvider } from "@mui/material/styles";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { buildAppTheme } from "../../theme/buildAppTheme.js";
import TrustSignalDrillIn from "./TrustSignalDrillIn.jsx";

const t = (key) => key;

const darkTheme = buildAppTheme("dark");

function renderDrillIn(props) {
  return renderToString(
    React.createElement(ThemeProvider, { theme: darkTheme }, React.createElement(TrustSignalDrillIn, props)),
  );
}

describe("TrustSignalDrillIn", () => {
  it("renders nothing when nothing to show", () => {
    const html = renderDrillIn({ criteria: {}, trustByFamily: {}, t });
    expect(html).toBe("");
  });

  it("includes warnings, validation, and advisory failure markers", () => {
    const html = renderDrillIn({
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
    });
    expect(html).toContain("retrieval_family.m1: orphan warning");
    expect(html).toContain("draft");
    expect(html).toContain("case_a");
    expect(html).toContain("retrieval_family.m1");
  });
});
