import { describe, expect, it, vi } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ThemeProvider } from "@mui/material/styles";

import { I18nProvider } from "../../i18n/I18nContext.jsx";
import { buildAppTheme } from "../../theme/buildAppTheme.js";

vi.mock("react-pdf", () => ({
  Document: ({ children, loading }) =>
    typeof loading === "function" ? <div data-testid="pdf-doc-loading">{String(Boolean(loading))}</div> : <div data-testid="pdf-doc">{children}</div>,
  Page: () => <div data-testid="pdf-page" />,
  pdfjs: { GlobalWorkerOptions: { workerSrc: "" } },
}));

const theme = buildAppTheme("dark");

describe("PdfViewer", () => {
  it("renders document shell with mocked react-pdf", async () => {
    const { default: PdfViewer } = await import("./PdfViewer.jsx");
    const html = renderToStaticMarkup(
      <I18nProvider>
        <ThemeProvider theme={theme}>
          <PdfViewer fileUrl="https://example.com/paper.pdf" />
        </ThemeProvider>
      </I18nProvider>,
    );
    expect(html).toContain("pdf-doc");
  });
});
