import { describe, expect, it } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ThemeProvider, createTheme } from "@mui/material/styles";

import WorkspaceLayout from "./WorkspaceLayout.jsx";

const theme = createTheme({ palette: { mode: "dark" } });

describe("WorkspaceLayout", () => {
  it("renders main and side slots", () => {
    const html = renderToStaticMarkup(
      <ThemeProvider theme={theme}>
        <WorkspaceLayout main={<div data-testid="main-slot" />} side={<div data-testid="side-slot" />} />
      </ThemeProvider>,
    );
    expect(html).toContain("main-slot");
    expect(html).toContain("side-slot");
  });
});
