// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { APPEARANCE_STORAGE_KEY } from "./appearanceConstants.js";
import {
  applyDocumentColorScheme,
  normalizeAppearancePreference,
  readAppearancePreference,
  resolveEffectiveAppearanceMode,
  writeAppearancePreference,
} from "./appearanceMode.js";

describe("normalizeAppearancePreference", () => {
  it("returns canonical values", () => {
    expect(normalizeAppearancePreference("dark")).toBe("dark");
    expect(normalizeAppearancePreference("light")).toBe("light");
    expect(normalizeAppearancePreference("system")).toBe("system");
  });

  it("falls back to system for unknown or empty", () => {
    expect(normalizeAppearancePreference("")).toBe("system");
    expect(normalizeAppearancePreference("auto")).toBe("system");
    expect(normalizeAppearancePreference(null)).toBe("system");
  });
});

describe("resolveEffectiveAppearanceMode", () => {
  it("respects explicit dark and light regardless of prefersDark", () => {
    expect(resolveEffectiveAppearanceMode("dark", false)).toBe("dark");
    expect(resolveEffectiveAppearanceMode("dark", true)).toBe("dark");
    expect(resolveEffectiveAppearanceMode("light", true)).toBe("light");
    expect(resolveEffectiveAppearanceMode("light", false)).toBe("light");
  });

  it("maps system to prefersDark", () => {
    expect(resolveEffectiveAppearanceMode("system", true)).toBe("dark");
    expect(resolveEffectiveAppearanceMode("system", false)).toBe("light");
  });
});

describe("localStorage integration", () => {
  const store = {};

  beforeEach(() => {
    Object.keys(store).forEach((k) => delete store[k]);
    vi.stubGlobal("window", {
      localStorage: {
        getItem: (key) => (key in store ? store[key] : null),
        setItem: (key, value) => {
          store[key] = String(value);
        },
        removeItem: (key) => {
          delete store[key];
        },
      },
      matchMedia: vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("readAppearancePreference returns system when unset", () => {
    expect(readAppearancePreference()).toBe("system");
  });

  it("writeAppearancePreference persists and read returns normalized value", () => {
    writeAppearancePreference("light");
    expect(store[APPEARANCE_STORAGE_KEY]).toBe("light");
    expect(readAppearancePreference()).toBe("light");
  });

  it("invalid stored value normalizes to system on read", () => {
    store[APPEARANCE_STORAGE_KEY] = "bogus";
    expect(readAppearancePreference()).toBe("system");
  });
});

describe("applyDocumentColorScheme", () => {
  it("sets dataset and style on documentElement", () => {
    applyDocumentColorScheme("light");
    expect(document.documentElement.dataset.colorScheme).toBe("light");
    expect(document.documentElement.style.colorScheme).toBe("light");
    applyDocumentColorScheme("dark");
    expect(document.documentElement.dataset.colorScheme).toBe("dark");
    expect(document.documentElement.style.colorScheme).toBe("dark");
  });
});
