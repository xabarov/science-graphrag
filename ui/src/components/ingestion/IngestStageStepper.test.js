import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import IngestStageStepper from "./IngestStageStepper.jsx";

describe("IngestStageStepper", () => {
  it("renders three stage statuses", () => {
    const html = renderToStaticMarkup(
      React.createElement(IngestStageStepper, {
        stages: [
          {
            name: "parse_pdf",
            status: "completed",
            duration_ms: 120,
            metrics: { pages: 14 },
          },
          {
            name: "extract_meta",
            status: "running",
            duration_ms: null,
            metrics: { references: 9 },
          },
          {
            name: "embed",
            status: "failed",
            duration_ms: 11,
            metrics: { chunks: 42 },
            error: "provider_timeout",
          },
        ],
      }),
    );

    expect(html).toContain("parse_pdf");
    expect(html).toContain("extract_meta");
    expect(html).toContain("embed");
    expect(html).toContain("provider_timeout");
  });
});
