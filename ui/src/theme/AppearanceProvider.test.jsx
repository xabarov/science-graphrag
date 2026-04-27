/** @vitest-environment jsdom */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { APPEARANCE_STORAGE_KEY } from "./appearanceConstants.js";
import { AppearanceProvider } from "./AppearanceProvider.jsx";
import { useAppearance } from "./useAppearance.js";

function Harness() {
  const { preference, effective, setPreference } = useAppearance();
  return (
    <div>
      <span data-testid="pref">{preference}</span>
      <span data-testid="eff">{effective}</span>
      <button type="button" onClick={() => setPreference("light")}>
        set-light
      </button>
      <button type="button" onClick={() => setPreference("system")}>
        set-system
      </button>
    </div>
  );
}

describe("AppearanceProvider", () => {
  const listeners = [];
  const mq = {
    matches: false,
    addEventListener: (_evt, fn) => {
      listeners.push(fn);
    },
    removeEventListener: (_evt, fn) => {
      const i = listeners.indexOf(fn);
      if (i >= 0) listeners.splice(i, 1);
    },
  };

  beforeEach(() => {
    listeners.length = 0;
    mq.matches = false;
    vi.stubGlobal("matchMedia", vi.fn(() => mq));
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    try {
      window.localStorage.clear();
    } catch {
      // ignore
    }
  });

  it("applies document color scheme from persisted preference", () => {
    window.localStorage.setItem(APPEARANCE_STORAGE_KEY, "light");
    render(
      <AppearanceProvider>
        <Harness />
      </AppearanceProvider>,
    );
    expect(screen.getByTestId("eff").textContent).toBe("light");
    expect(document.documentElement.dataset.colorScheme).toBe("light");
    expect(document.documentElement.style.colorScheme).toBe("light");
  });

  it("updates storage and document when preference changes", () => {
    render(
      <AppearanceProvider>
        <Harness />
      </AppearanceProvider>,
    );
    expect(screen.getByTestId("pref").textContent).toBe("system");
    fireEvent.click(screen.getByRole("button", { name: "set-light" }));
    expect(screen.getByTestId("pref").textContent).toBe("light");
    expect(screen.getByTestId("eff").textContent).toBe("light");
    expect(window.localStorage.getItem(APPEARANCE_STORAGE_KEY)).toBe("light");
    expect(document.documentElement.dataset.colorScheme).toBe("light");
  });

  it("when system, reacts to prefers-color-scheme media change", async () => {
    render(
      <AppearanceProvider>
        <Harness />
      </AppearanceProvider>,
    );
    expect(screen.getByTestId("eff").textContent).toBe("light");

    fireEvent.click(screen.getByRole("button", { name: "set-system" }));
    expect(screen.getByTestId("pref").textContent).toBe("system");

    mq.matches = true;
    listeners.forEach((fn) => fn());
    await waitFor(() => {
      expect(screen.getByTestId("eff").textContent).toBe("dark");
    });
    expect(document.documentElement.dataset.colorScheme).toBe("dark");
  });
});
