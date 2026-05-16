import { describe, expect, it } from "vitest";

import {
  resolveSettingsSectionDescription,
  resolveSettingsSectionLabel,
} from "./settingsSectionText.js";

describe("settingsSectionText", () => {
  const section = { id: "custom", label: "API label", description: "API description" };
  const t = (key) => key;

  it("falls back to API catalog strings when i18n keys are missing", () => {
    expect(resolveSettingsSectionLabel(section, t)).toBe("API label");
    expect(resolveSettingsSectionDescription(section, t)).toBe("API description");
  });

  it("prefers i18n when keys exist", () => {
    const localized = (key) =>
      key === "settings.snapshot.llm.label" ? "Localized LLM" : key;
    expect(resolveSettingsSectionLabel({ id: "llm", label: "LLM" }, localized)).toBe("Localized LLM");
  });
});
