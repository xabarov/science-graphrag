import { describe, expect, it } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ThemeProvider, createTheme } from "@mui/material/styles";

import MarkdownViewCore, { preprocessReaderMarkdown } from "./MarkdownViewCore.jsx";

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

  it("treats single newlines as line breaks (remark-breaks) for OCR-style text", () => {
    const html = renderMarkdown("Line one\nLine two");
    expect(html).toContain("br");
    expect(html).toContain("Line one");
    expect(html).toContain("Line two");
  });

  it("unwraps outer ```markdown fence so emphasis parses (VL-style payload)", () => {
    const raw = "```markdown\n\n**Falcon-M1** abstract\n\n```";
    expect(preprocessReaderMarkdown(raw).trim()).toBe("**Falcon-M1** abstract");
    const html = renderMarkdown(raw);
    expect(html).toContain("<strong");
    expect(html).toContain("Falcon-M1");
  });

  it("strips uniform 4-space indent so VL dumps are not one big code block", () => {
    const raw = "    **bold** here\n    second line";
    expect(preprocessReaderMarkdown(raw).trim()).toBe("**bold** here\nsecond line");
    const html = renderMarkdown(raw);
    expect(html).toContain("<strong");
    expect(html).not.toContain("<pre>");
  });
});
