/** @vitest-environment jsdom */
import { ThemeProvider } from "@mui/material/styles";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { buildAppTheme } from "../../../theme/buildAppTheme.js";
import { CitationBodyExpandable } from "./CitationBodyExpandable.jsx";

const theme = buildAppTheme("dark");

afterEach(() => {
  cleanup();
});

describe("CitationBodyExpandable", () => {
  it("renders dashed placeholder when passage missing", () => {
    render(
      <ThemeProvider theme={theme}>
        <CitationBodyExpandable t={(k) => k} citation={{}} defaultExpanded />
      </ThemeProvider>,
    );
    expect(screen.getByText("askPanel.citation.noSnippet")).toBeTruthy();
  });

  it("renders nothing when passage missing and suppressMissingPlaceholder", () => {
    render(
      <ThemeProvider theme={theme}>
        <CitationBodyExpandable t={(k) => k} citation={{}} suppressMissingPlaceholder defaultExpanded />
      </ThemeProvider>,
    );
    expect(screen.queryByText("askPanel.citation.noSnippet")).toBeNull();
  });
});
