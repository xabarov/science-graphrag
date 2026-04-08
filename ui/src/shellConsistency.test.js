import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  ADMIN_MODE_STORAGE_KEY,
  isAdminPath,
  resolveAdminModeFlag,
} from "./components/layout/adminVisibility.js";

describe("adminVisibility", () => {
  beforeEach(() => {
    const store = {};
    vi.stubGlobal("window", {
      localStorage: {
        getItem: (key) => (key in store ? store[key] : null),
        setItem: (key, value) => {
          store[key] = String(value);
        },
      },
    });
  });

  it("prefers explicit local storage override over env defaults", () => {
    expect(resolveAdminModeFlag({ envValue: "true", storageValue: "false" })).toBe(false);
    expect(resolveAdminModeFlag({ envValue: "false", storageValue: "true" })).toBe(true);
    expect(resolveAdminModeFlag({ envValue: "false", storageValue: null })).toBe(false);
  });

  it("recognizes canonical and legacy admin paths", () => {
    expect(isAdminPath("/admin")).toBe(true);
    expect(isAdminPath("/admin/settings")).toBe(true);
    expect(isAdminPath("/benchmark")).toBe(true);
    expect(isAdminPath("/workspace")).toBe(false);
  });

  it("stores admin mode key in a stable local-storage slot", () => {
    window.localStorage.setItem(ADMIN_MODE_STORAGE_KEY, "false");
    expect(window.localStorage.getItem(ADMIN_MODE_STORAGE_KEY)).toBe("false");
  });
});
