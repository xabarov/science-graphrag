/** @vitest-environment jsdom */
import { ThemeProvider } from "@mui/material/styles";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { buildAppTheme } from "../../theme/buildAppTheme.js";
import { IdeaSuggestionsBlock, QuoteCandidatesBlock, RelationTraceBlock } from "./ChatTypedBlocks.jsx";

const themeDark = buildAppTheme("dark");
const themeLight = buildAppTheme("light");

function t(key) {
  return key;
}

describe("ChatTypedBlocks chrome", () => {
  it("wraps quote candidates in a single structured block with title", () => {
    render(
      <ThemeProvider theme={themeDark}>
        <QuoteCandidatesBlock
          t={t}
          candidates={[{ quote_text: "hello", work_id: "w1", section: "1" }]}
        />
      </ThemeProvider>,
    );
    expect(screen.getByText("chat.typed.quotesTitle")).toBeTruthy();
    expect(screen.getByText(/“hello”/)).toBeTruthy();
  });

  it("uses shared chrome for relation trace", () => {
    const { container } = render(
      <ThemeProvider theme={themeDark}>
        <RelationTraceBlock t={t} relationTrace={{ a: 1 }} />
      </ThemeProvider>,
    );
    expect(container.querySelector("pre")).toBeTruthy();
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
        <QuoteCandidatesBlock t={t} candidates={[{ quote_text: "light", work_id: "w2" }]} />
      </ThemeProvider>,
    );
    expect(screen.getByText(/“light”/)).toBeTruthy();
  });
});
