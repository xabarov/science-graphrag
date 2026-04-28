import { describe, expect, it } from "vitest";

import { defaultLauncherPrefs } from "./benchmarkLauncherConfig.js";
import {
  hasLocalModelApiOverride,
  mergeLauncherPrefsWithServer,
  serverBenchmarkRowToCamel,
} from "./mergeBenchmarkLauncherPrefs.js";

describe("serverBenchmarkRowToCamel", () => {
  it("maps snake_case API row", () => {
    expect(
      serverBenchmarkRowToCamel({
        model_profile: "custom",
        custom_model_id: "x/y",
        gold_source: "teacher_gold",
        threshold_profile: "student_mistral",
        base_url_override: "https://api.example/v1",
        api_key_env_name: "MY_KEY",
      }),
    ).toEqual({
      modelProfile: "custom",
      customModelId: "x/y",
      goldSource: "teacher_gold",
      thresholdProfile: "student_mistral",
      baseUrlOverride: "https://api.example/v1",
      apiKeyEnvName: "MY_KEY",
    });
  });
});

describe("mergeLauncherPrefsWithServer", () => {
  it("returns normalized local when server missing", () => {
    const local = defaultLauncherPrefs();
    expect(mergeLauncherPrefsWithServer({ rawLocalPrefs: local, serverBenchmark: null })).toEqual(local);
  });

  it("applies server gold when user has not overridden gold", () => {
    const local = defaultLauncherPrefs();
    const merged = mergeLauncherPrefsWithServer({
      rawLocalPrefs: local,
      serverBenchmark: {
        by_family: {
          layer1: {
            model_profile: "env_default",
            custom_model_id: "",
            gold_source: "teacher_gold",
            threshold_profile: "student_mistral",
            base_url_override: "",
            api_key_env_name: "",
          },
        },
      },
    });
    expect(merged.byFamily.layer1.goldSource).toBe("teacher_gold");
    expect(merged.byFamily.layer1.thresholdProfile).toBe("student_mistral");
    expect(merged.byFamily.layer1.modelProfile).toBe("env_default");
  });

  it("keeps local gold when userOverrides.goldSource", () => {
    const local = defaultLauncherPrefs();
    local.byFamily.layer1.goldSource = "curated_gold";
    local.byFamily.layer1.userOverrides = { goldSource: true, thresholdProfile: false };
    const merged = mergeLauncherPrefsWithServer({
      rawLocalPrefs: local,
      serverBenchmark: {
        by_family: {
          layer1: {
            model_profile: "env_default",
            gold_source: "teacher_gold",
            threshold_profile: "student_mistral",
          },
        },
      },
    });
    expect(merged.byFamily.layer1.goldSource).toBe("curated_gold");
    expect(merged.byFamily.layer1.thresholdProfile).toBe("student_mistral");
  });

  it("keeps local model block when user customized model profile", () => {
    const local = defaultLauncherPrefs();
    local.byFamily.layer1.modelProfile = "custom";
    local.byFamily.layer1.customModelId = "org/model";
    const merged = mergeLauncherPrefsWithServer({
      rawLocalPrefs: local,
      serverBenchmark: {
        by_family: {
          layer1: {
            model_profile: "env_default",
            custom_model_id: "",
            gold_source: "teacher_gold",
            threshold_profile: "from_gold",
          },
        },
      },
    });
    expect(merged.byFamily.layer1.modelProfile).toBe("custom");
    expect(merged.byFamily.layer1.customModelId).toBe("org/model");
    expect(merged.byFamily.layer1.goldSource).toBe("teacher_gold");
  });
});

describe("hasLocalModelApiOverride", () => {
  it("is false for code defaults", () => {
    const d = defaultLauncherPrefs().byFamily.layer1;
    expect(hasLocalModelApiOverride("layer1", d)).toBe(false);
  });

  it("is true when base URL set", () => {
    const d = { ...defaultLauncherPrefs().byFamily.layer1, baseUrlOverride: "https://x" };
    expect(hasLocalModelApiOverride("layer1", d)).toBe(true);
  });
});
