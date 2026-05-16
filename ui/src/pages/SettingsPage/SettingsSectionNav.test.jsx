/** @vitest-environment jsdom */
import React from "react";
import { ThemeProvider } from "@mui/material/styles";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../../i18n/I18nContext.jsx";
import { buildAppTheme } from "../../theme/buildAppTheme.js";

import SettingsSectionNav from "./SettingsSectionNav.jsx";

const theme = buildAppTheme("dark");

const sections = [
  { id: "general", label: "General", description: "General desc" },
  { id: "llm", label: "LLM", description: "LLM desc" },
];

function renderNav(props) {
  return render(
    <ThemeProvider theme={theme}>
      <I18nProvider>
        <SettingsSectionNav sections={sections} activeSectionId="general" onSelect={vi.fn()} {...props} />
      </I18nProvider>
    </ThemeProvider>,
  );
}

afterEach(() => {
  cleanup();
});

describe("SettingsSectionNav", () => {
  it("renders section labels without rollout status chips", () => {
    renderNav();
    const general = screen.getByRole("button", { name: /General/i });
    expect(general.textContent).toMatch(/global defaults/i);
    expect(screen.queryByText(/^(Ready|Готово|Soon|Скоро)$/i)).toBeNull();
  });

  it("calls onSelect when a section is activated", () => {
    const onSelect = vi.fn();
    renderNav({ onSelect });
    fireEvent.click(screen.getByRole("button", { name: /LLM/i }));
    expect(onSelect).toHaveBeenCalledWith("llm");
  });

  it("marks the active section for assistive tech", () => {
    renderNav();
    expect(screen.getByRole("button", { name: /General/i }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByRole("button", { name: /LLM/i }).hasAttribute("aria-current")).toBe(false);
  });
});
