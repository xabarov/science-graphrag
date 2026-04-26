/** @vitest-environment jsdom */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../../i18n/I18nContext.jsx";
import ReaderWorkBody from "./ReaderWorkBody.jsx";

const theme = createTheme();

vi.mock("./useReaderWorkData.js", () => ({
  useReaderWorkData: vi.fn(),
}));

vi.mock("./useReaderChunksState.js", () => ({
  useReaderChunksState: vi.fn(),
}));

const { useReaderWorkData } = await import("./useReaderWorkData.js");
const { useReaderChunksState } = await import("./useReaderChunksState.js");

function renderReader() {
  return render(
    <I18nProvider>
      <ThemeProvider theme={theme}>
        <ReaderWorkBody workId="w1" />
      </ThemeProvider>
    </I18nProvider>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ReaderWorkBody", () => {
  it("prefers extracted-body over chunk join when both exist (ADR 022)", async () => {
    useReaderWorkData.mockReturnValue({
      detail: { title: "T", abstract: "" },
      chunks: { items: [{ order: 0, text: "chunk-only", section_path: "S" }], total: 1 },
      extractedBodyPayload: { available: true, text: "# FromArtifact\n\nbody", truncated: false },
      loading: false,
      error: null,
      pdfAvailable: false,
      viewMode: "ocr",
      setViewMode: vi.fn(),
    });
    useReaderChunksState.mockReturnValue({
      chunksOpen: false,
      setChunksOpen: vi.fn(),
      orderedItems: [],
      combinedMarkdown: "## S\n\nchunk-only",
      isChunkHighlighted: () => false,
    });

    renderReader();
    await waitFor(() => {
      expect(screen.getByTestId("reader-markdown-body")).toBeTruthy();
    });
    expect(screen.getByTestId("reader-markdown-body").textContent).toContain("FromArtifact");
    expect(screen.getByTestId("reader-markdown-body").textContent).not.toContain("chunk-only");
  });

  it("uses chunk join when extracted-body is unavailable", async () => {
    useReaderWorkData.mockReturnValue({
      detail: { title: "T", abstract: "" },
      chunks: { items: [{ order: 0, text: "only-chunks", section_path: "S" }], total: 1 },
      extractedBodyPayload: { available: false, text: "", truncated: false },
      loading: false,
      error: null,
      pdfAvailable: false,
      viewMode: "ocr",
      setViewMode: vi.fn(),
    });
    useReaderChunksState.mockReturnValue({
      chunksOpen: false,
      setChunksOpen: vi.fn(),
      orderedItems: [],
      combinedMarkdown: "## S\n\nonly-chunks",
      isChunkHighlighted: () => false,
    });

    renderReader();
    await waitFor(() => {
      expect(screen.getByTestId("reader-markdown-body")).toBeTruthy();
    });
    expect(screen.getByTestId("reader-markdown-body").textContent).toContain("only-chunks");
  });
});
