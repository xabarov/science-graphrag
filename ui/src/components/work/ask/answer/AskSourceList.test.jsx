/** @vitest-environment jsdom */
import React from "react";
import { describe, expect, it, afterEach, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { cleanup, render, screen, within } from "@testing-library/react";
import { ThemeProvider } from "@mui/material/styles";

import { buildAppTheme } from "../../../../theme/buildAppTheme.js";
import { AskSourceList } from "./AskSourceList.jsx";

const appTheme = buildAppTheme("dark");

afterEach(() => {
  cleanup();
});

function renderWithTheme(node) {
  return render(
    <MemoryRouter>
      <ThemeProvider theme={appTheme}>{node}</ThemeProvider>
    </MemoryRouter>,
  );
}

const testMessages = {
  "askPanel.citations.title": "Citations",
  "askPanel.citations.inventoryTitle": "Found papers",
  "askPanel.citations.webTitle": "Web sources",
  "askPanel.citations.none": "No citations",
  "askPanel.citation.noSnippetBulkAll": "No passages in all citations",
  "askPanel.citation.noSnippetBulkPartial": "No passages in some citations",
  "askPanel.citation.rankLabel": "Citation #{{rank}}",
  "askPanel.citation.workRankLabel": "Paper #{{rank}}",
  "askPanel.citation.webRankLabel": "Source #{{rank}}",
  "askPanel.citation.sourceLine": "Source: {{title}}",
  "askPanel.citation.workIdLine": "work_id: {{id}}",
  "askPanel.citation.noSnippet": "No snippet",
  "askPanel.citation.passageLabel": "Passage",
  "askPanel.citation.expandShow": "Show",
  "askPanel.citation.expandHide": "Hide",
  "askPanel.citation.copy": "Copy",
  "askPanel.citation.copied": "Copied",
  "askPanel.citation.tooltipArticle": "Open article",
  "askPanel.citation.tooltipGraphWork": "Open work graph",
  "askPanel.citation.linkReader": "Reader",
  "askPanel.citation.linkGraph": "Graph",
  "askPanel.citation.linkWeb": "Open link",
  "askPanel.citation.tooltipWebSource": "Open external source",
  "askPanel.citation.linkReadPdf": "Read PDF",
  "askPanel.citation.tooltipReadPdf": "Read PDF and extract text",
  "askPanel.citation.noWork": "No work",
  "askPanel.citation.trust.external": "External",
  "askPanel.citation.trust.abstract": "Abstract",
  "askPanel.citation.trust.metadataOnly": "Metadata only",
  "askPanel.citation.trust.fullText": "Full text",
  "askPanel.citation.trust.webSummary": "Web summary",
  "askPanel.citation.trust.oaLink": "OA link",
  "askPanel.citation.trust.pdfRead": "PDF read",
  "askPanel.citation.fallback.host_not_allowed": "URL blocked",
  "askPanel.chunkLabel": "chunk",
};

function t(key, vars) {
  let value = testMessages[key] ?? key;
  if (vars && typeof vars === "object") {
    for (const [name, raw] of Object.entries(vars)) {
      value = value.replaceAll(`{{${name}}}`, String(raw));
    }
  }
  return value;
}

describe("AskSourceList", () => {
  it("shows inventory label for work-only list", () => {
    renderWithTheme(
      <AskSourceList
        t={t}
        citations={[{ work_id: "w-1", title: "Paper One" }]}
        answerClass="inventory"
        workspaceId="ws-1"
        isRunActive={false}
        hideStructuredCitations={false}
        chatDetailLevel="simple"
      />,
    );
    expect(screen.getByText("Found papers")).toBeTruthy();
    expect(screen.queryByText("Citations")).toBeNull();
  });

  it("suppresses no-snippet alert for full work-only list", () => {
    renderWithTheme(
      <AskSourceList
        t={t}
        citations={[
          { work_id: "w-1", title: "Paper One" },
          { work_id: "w-2", title: "Paper Two" },
        ]}
        answerClass="inventory"
        workspaceId="ws-1"
        isRunActive={false}
        hideStructuredCitations={false}
        chatDetailLevel="simple"
      />,
    );
    expect(screen.queryByText("No passages in all citations")).toBeNull();
  });

  it("shows secondary work_id line in detailed mode for work-only item", () => {
    renderWithTheme(
      <AskSourceList
        t={t}
        citations={[{ work_id: "w-det", title: "Detailed Work" }]}
        answerClass="inventory"
        workspaceId="ws-1"
        isRunActive={false}
        hideStructuredCitations={false}
        chatDetailLevel="detailed"
      />,
    );
    expect(screen.getByText("work_id: w-det")).toBeTruthy();
  });

  it("puts paper title on source line, not in rank headline (simple)", () => {
    renderWithTheme(
      <AskSourceList
        t={t}
        citations={[
          {
            work_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            title: "Neural Scaling Laws",
            excerpt: "Supervised pre-training…",
            chunk_fingerprint: "fp-1",
          },
        ]}
        answerClass="grounded_explanation"
        workspaceId="ws-1"
        isRunActive={false}
        hideStructuredCitations={false}
        chatDetailLevel="simple"
      />,
    );
    expect(screen.getByText("Citation #1")).toBeTruthy();
    expect(screen.getByText("Source: Neural Scaling Laws")).toBeTruthy();
    expect(screen.queryByText(/aaaaaaaa/)).toBeNull();
  });

  it("shows work_id and source line in detailed mode when title present", () => {
    const { container } = renderWithTheme(
      <AskSourceList
        t={t}
        citations={[
          {
            work_id: "w-x",
            title: "Paper X",
            excerpt: "Body",
            chunk_fingerprint: "fp-z",
          },
        ]}
        answerClass="grounded_explanation"
        workspaceId="ws-1"
        isRunActive={false}
        hideStructuredCitations={false}
        chatDetailLevel="detailed"
      />,
    );
    const el = container.querySelector('[data-testid="citation-block-0"]');
    expect(el).toBeTruthy();
    const block = within(el);
    expect(block.getByText("Citation #1")).toBeTruthy();
    expect(block.queryByText(/Citation #1 ·/)).toBeNull();
    expect(block.getByText("work_id: w-x")).toBeTruthy();
    expect(block.getByText("Source: Paper X")).toBeTruthy();
  });

  it("renders external web link for web citations", () => {
    const { container } = renderWithTheme(
      <AskSourceList
        t={t}
        answerClass="grounded_explanation"
        citations={[
          {
            source_type: "web",
            title: "Crossref hit",
            url: "https://doi.org/10.9999/demo",
            excerpt: "Summary text.",
          },
        ]}
        chatDetailLevel="detailed"
      />,
    );
    const link = container.querySelector('a[href="https://doi.org/10.9999/demo"]');
    expect(link).toBeTruthy();
    expect(link.textContent).toContain("Open link");
    expect(screen.getByText("Web sources")).toBeTruthy();
    expect(screen.getByText("Source #1")).toBeTruthy();
  });

  it("renders Read PDF action for PDF-like web sources", () => {
    const onReadPdfSource = vi.fn();
    renderWithTheme(
      <AskSourceList
        t={t}
        answerClass="grounded_explanation"
        onReadPdfSource={onReadPdfSource}
        pdfReadingMode="ask"
        citations={[
          {
            source_type: "web",
            title: "ArXiv PDF",
            url: "https://arxiv.org/pdf/1706.03762.pdf",
            excerpt: "Transformer paper",
          },
        ]}
        chatDetailLevel="detailed"
      />,
    );
    const btn = screen.getByRole("button", { name: "Read PDF and extract text" });
    expect(btn).toBeTruthy();
    btn.click();
    expect(onReadPdfSource).toHaveBeenCalledWith("https://arxiv.org/pdf/1706.03762.pdf");
  });

  it("hides Read PDF action when pdf reading mode is off", () => {
    renderWithTheme(
      <AskSourceList
        t={t}
        answerClass="grounded_explanation"
        onReadPdfSource={() => {}}
        pdfReadingMode="off"
        citations={[
          {
            source_type: "web",
            title: "Publisher PDF",
            url: "https://example.org/paper.pdf",
            excerpt: "Body",
          },
        ]}
        chatDetailLevel="detailed"
      />,
    );
    expect(screen.queryByRole("button", { name: "Read PDF and extract text" })).toBeNull();
  });

  it("renders trust badges and fallback for web citation", () => {
    renderWithTheme(
      <AskSourceList
        t={t}
        answerClass="grounded_explanation"
        citations={[
          {
            source_type: "web",
            title: "Blocked",
            url: "https://publisher.example/x",
            excerpt: "Meta",
            is_external: true,
            evidence_mode: "abstract",
            provenance_kind: "arxiv_abstract",
            fallback_reason: "host_not_allowed",
          },
        ]}
        chatDetailLevel="detailed"
      />,
    );
    expect(screen.getByTestId("citation-trust-badges-0")).toBeTruthy();
    expect(screen.getByText("External")).toBeTruthy();
    expect(screen.getByText("Abstract")).toBeTruthy();
    expect(screen.getByTestId("citation-fallback-0").textContent).toContain("URL blocked");
  });
});
