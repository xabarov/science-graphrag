/** @vitest-environment jsdom */
import { ThemeProvider } from "@mui/material/styles";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup } from "@testing-library/react";

import { buildAppTheme } from "../../../../theme/buildAppTheme.js";
import {
  IdeaSuggestionsBlock,
  InventoryBlock,
  QuoteCandidatesBlock,
  RelationTraceBlock,
} from "./ChatTypedBlocks.jsx";

const themeDark = buildAppTheme("dark");
const themeLight = buildAppTheme("light");

afterEach(() => {
  cleanup();
});

function t(key) {
  return key;
}

describe("ChatTypedBlocks chrome", () => {
  it("wraps quote candidates in a single structured block with title", () => {
    render(
      <ThemeProvider theme={themeDark}>
        <QuoteCandidatesBlock
          t={t}
          chatDetailLevel="detailed"
          candidates={[{ quote_text: "hello", work_id: "w1", section: "1" }]}
        />
      </ThemeProvider>,
    );
    expect(screen.getByText("chat.typed.quotesTitle")).toBeTruthy();
    expect(screen.getByText(/“hello”/)).toBeTruthy();
  });

  it("collapses quote candidates in simple mode until expanded", () => {
    render(
      <ThemeProvider theme={themeDark}>
        <QuoteCandidatesBlock
          t={t}
          chatDetailLevel="simple"
          candidates={[{ quote_text: "hidden", work_id: "w1" }]}
        />
      </ThemeProvider>,
    );
    expect(screen.queryByText("chat.typed.quotesTitle")).toBeNull();
    expect(screen.queryByText(/“hidden”/)).toBeNull();
    fireEvent.click(screen.getByTestId("quote-candidates-toggle"));
    expect(screen.getByText("chat.typed.quotesTitle")).toBeTruthy();
    expect(screen.getByText(/“hidden”/)).toBeTruthy();
  });

  it("uses shared chrome for relation trace in detailed mode", () => {
    const { container } = render(
      <ThemeProvider theme={themeDark}>
        <RelationTraceBlock t={t} chatDetailLevel="detailed" relationTrace={{ a: 1 }} />
      </ThemeProvider>,
    );
    expect(container.querySelector("pre")).toBeTruthy();
  });

  it("hides relation trace in simple mode", () => {
    const { container } = render(
      <ThemeProvider theme={themeDark}>
        <RelationTraceBlock t={t} chatDetailLevel="simple" relationTrace={{ a: 1 }} />
      </ThemeProvider>,
    );
    expect(container.querySelector("pre")).toBeNull();
  });

  it("hides paper matches in simple mode when citations exist and evidence is not weak", () => {
    const { container } = render(
      <ThemeProvider theme={themeDark}>
        <InventoryBlock
          t={t}
          chatDetailLevel="simple"
          citationCount={2}
          hasWeakEvidence={false}
          inventory={{ paper_matches: ["One", "Two", "Four"] }}
        />
      </ThemeProvider>,
    );
    expect(container.textContent).not.toContain("chat.typed.matchesTitle");
  });

  it("shows paper matches in simple mode when weak_evidence despite citations", () => {
    render(
      <ThemeProvider theme={themeDark}>
        <InventoryBlock
          t={t}
          chatDetailLevel="simple"
          citationCount={1}
          hasWeakEvidence
          inventory={{ paper_matches: ["Alpha"] }}
        />
      </ThemeProvider>,
    );
    expect(screen.getByText("chat.typed.matchesTitle")).toBeTruthy();
    expect(screen.getByText("Alpha")).toBeTruthy();
  });

  it("hides work_id under paper titles in simple inventory but shows in detailed", () => {
    const inv = { papers: [{ title: "My Paper", work_id: "uuid-99" }] };
    const { rerender } = render(
      <ThemeProvider theme={themeDark}>
        <InventoryBlock t={t} chatDetailLevel="simple" inventory={inv} />
      </ThemeProvider>,
    );
    expect(screen.getByText("My Paper")).toBeTruthy();
    expect(screen.queryByText("uuid-99")).toBeNull();
    rerender(
      <ThemeProvider theme={themeDark}>
        <InventoryBlock t={t} chatDetailLevel="detailed" inventory={inv} />
      </ThemeProvider>,
    );
    expect(screen.getByText("uuid-99")).toBeTruthy();
  });

  it("uses shared chrome for idea suggestions", () => {
    const { container } = render(
      <ThemeProvider theme={themeDark}>
        <IdeaSuggestionsBlock t={t} suggestions={["one"]} />
      </ThemeProvider>,
    );
    expect(container.textContent).toContain("one");
  });

  it("renders quote block in light theme without crashing", () => {
    render(
      <ThemeProvider theme={themeLight}>
        <QuoteCandidatesBlock
          t={t}
          chatDetailLevel="detailed"
          candidates={[{ quote_text: "light", work_id: "w2" }]}
        />
      </ThemeProvider>,
    );
    expect(screen.getByText(/“light”/)).toBeTruthy();
  });

  it("shows work title as primary line when present on quote candidate", () => {
    render(
      <ThemeProvider theme={themeDark}>
        <QuoteCandidatesBlock
          t={t}
          chatDetailLevel="detailed"
          candidates={[
            {
              quote_text: "body",
              work_id: "uuid-1",
              title: "Paper Title",
            },
          ]}
        />
      </ThemeProvider>,
    );
    expect(screen.getByText("Paper Title")).toBeTruthy();
    expect(screen.getByText(/uuid-1/)).toBeTruthy();
  });
});
