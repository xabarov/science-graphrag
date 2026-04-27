/** @vitest-environment jsdom */
import React from "react";
import { ThemeProvider } from "@mui/material/styles";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { I18nProvider } from "../../i18n/I18nContext.jsx";
import { buildAppTheme } from "../../theme/buildAppTheme.js";

import BenchmarkAnalysisOverview from "./BenchmarkAnalysisOverview.jsx";

const theme = buildAppTheme("dark");

afterEach(() => {
  cleanup();
});

function renderOverview(props) {
  return render(
    <ThemeProvider theme={theme}>
      <I18nProvider>
        <BenchmarkAnalysisOverview {...props} />
      </I18nProvider>
    </ThemeProvider>,
  );
}

describe("BenchmarkAnalysisOverview", () => {
  it("renders empty state", () => {
    renderOverview({
      session: null,
      loading: false,
      error: null,
      onReload: () => {},
      selectedExperimentId: null,
      selectedVariantId: null,
      selectedRow: null,
      selectedCell: null,
      onSelectCell: () => {},
      compareResult: null,
      compareLoading: false,
      compareError: null,
      compareCurrentRunId: null,
      onOpenWorkbench: () => {},
      onOpenCompare: () => {},
      onOpenResults: () => {},
    });
    expect(screen.getByText("Analysis needs a selected run set")).toBeTruthy();
  });

  it("renders matrix and delta section for selected row", () => {
    const session = {
      source: "url",
      runIds: ["r1", "r2"],
      variantIds: ["env_default", "mini"],
      rows: [
        {
          experimentId: "layer1_nightly",
          experiment: {
            titleKey: "benchmarkCatalog.experiment.layer1Nightly.title",
            descriptionKey: "benchmarkCatalog.experiment.layer1Nightly.description",
          },
          variants: [
            {
              variantId: "env_default",
              variantLabel: "env_default",
              runId: "r1",
              status: "completed",
              isBaseline: true,
              summary: { caseCount: 5, passCount: 5, failCount: 0, avgNamesF1: 0.91 },
            },
            {
              variantId: "mini",
              variantLabel: "mini",
              runId: "r2",
              status: "completed",
              isBaseline: false,
              summary: { caseCount: 5, passCount: 4, failCount: 1, avgNamesF1: 0.87 },
            },
          ],
        },
      ],
    };
    renderOverview({
      session,
      loading: false,
      error: null,
      onReload: () => {},
      selectedExperimentId: "layer1_nightly",
      selectedVariantId: "mini",
      selectedRow: session.rows[0],
      selectedCell: session.rows[0].variants[1],
      onSelectCell: () => {},
      compareResult: {
        summary: {
          regression_count: 1,
          improvement_count: 0,
          unchanged_count: 2,
          missing_in_current: [],
          added_in_current: [],
        },
        regressions: [{ case_id: "case-1", metric: "m1", baseline: 1, current: 0, delta: -1 }],
      },
      compareLoading: false,
      compareError: null,
      compareCurrentRunId: "r2",
      onOpenWorkbench: () => {},
      onOpenCompare: () => {},
      onOpenResults: () => {},
    });
    expect(screen.getByText("Analysis-first comparison")).toBeTruthy();
    expect(screen.getAllByText("Layer-1 nightly").length).toBeGreaterThan(0);
    expect(screen.getByText("Per-experiment delta summary")).toBeTruthy();
    expect(screen.getByText("Top regressions")).toBeTruthy();
  });
});
