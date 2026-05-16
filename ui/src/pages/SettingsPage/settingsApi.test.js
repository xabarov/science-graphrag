import { describe, expect, it } from "vitest";

import {
  getSettingsSnapshot,
  getSettingsSchema,
  revealLlmTaskSecret,
  testAgentToolsSource,
  updateAgentToolsSettings,
} from "./settingsApi.js";

describe("settingsApi auth headers", () => {
  it("keeps callable exports for settings page wiring", () => {
    expect(typeof getSettingsSchema).toBe("function");
    expect(typeof getSettingsSnapshot).toBe("function");
    expect(typeof updateAgentToolsSettings).toBe("function");
    expect(typeof testAgentToolsSource).toBe("function");
    expect(typeof revealLlmTaskSecret).toBe("function");
  });
});
