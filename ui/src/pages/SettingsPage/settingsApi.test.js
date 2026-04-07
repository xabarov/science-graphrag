import { describe, expect, it } from "vitest";

import { getSettingsSnapshot, getSettingsSchema } from "./settingsApi.js";

describe("settingsApi auth headers", () => {
  it("keeps callable exports for settings page wiring", () => {
    expect(typeof getSettingsSchema).toBe("function");
    expect(typeof getSettingsSnapshot).toBe("function");
  });
});
