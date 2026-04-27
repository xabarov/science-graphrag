/** @vitest-environment jsdom */
import React from "react";
import { ThemeProvider } from "@mui/material/styles";
import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { buildAppTheme } from "./buildAppTheme.js";
import { useAppTokens } from "./useAppTokens.js";

function wrapper(mode) {
  const theme = buildAppTheme(mode);
  return function W({ children }) {
    return <ThemeProvider theme={theme}>{children}</ThemeProvider>;
  };
}

describe("useAppTokens", () => {
  it("returns dark surface tokens", () => {
    const { result } = renderHook(() => useAppTokens(), { wrapper: wrapper("dark") });
    expect(result.current.surface.app).toBe("#0a0a0a");
    expect(result.current.border.default).toContain("255");
  });

  it("returns light surface tokens", () => {
    const { result } = renderHook(() => useAppTokens(), { wrapper: wrapper("light") });
    expect(result.current.surface.app).toContain("f5");
    expect(result.current.text.primary).toContain("15,23,42");
  });
});
