import { describe, expect, it } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ThemeProvider, createTheme } from "@mui/material/styles";

import MarkdownViewCore from "./MarkdownViewCore.jsx";

const theme = createTheme({ palette: { mode: "dark" } });

function renderMarkdown(markdown) {
  return renderToStaticMarkup(
    <ThemeProvider theme={theme}>
      <MarkdownViewCore markdown={markdown} />
    </ThemeProvider>,
  );
}

describe("MarkdownViewCore", () => {
  it("renders headings and strong emphasis from markdown", () => {
    const html = renderMarkdown("# Hi\n\n**bold**");
    expect(html).toContain("<h1");
    expect(html).toContain("Hi");
    expect(html).toContain("<strong");
    expect(html).toContain("bold");
  });

  it("renders GFM strikethrough via remark-gfm", () => {
    const html = renderMarkdown("~~gone~~");
    expect(html).toContain("del");
    expect(html).toContain("gone");
  });
});
