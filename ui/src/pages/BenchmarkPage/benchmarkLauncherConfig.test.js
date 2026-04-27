import { describe, expect, it } from "vitest";

import {
  buildExecutionSummary,
  buildRunPayload,
  humanizeLauncherError,
  mergeProfileDefaults,
  normalizeLauncherPrefs,
  validateLauncherConfig,
} from "./benchmarkLauncherConfig.js";

describe("normalizeLauncherPrefs", () => {
  it("keeps family-scoped prefs without cross-family overwrite", () => {
    const prefs = normalizeLauncherPrefs({
      activeFamily: "layer2",
      byFamily: {
        layer1: { goldSource: "teacher_gold", thresholdProfile: "student_mistral" },
        layer2: { modelProfile: "custom", customModelId: "foo/bar" },
      },
    });
    expect(prefs.activeFamily).toBe("layer2");
    expect(prefs.byFamily.layer1.goldSource).toBe("teacher_gold");
    expect(prefs.byFamily.layer2.customModelId).toBe("foo/bar");
    expect(prefs.byFamily.layer2.goldSource).toBe("semantic_gold");
  });
});

describe("mergeProfileDefaults", () => {
  it("applies defaults only when there is no explicit override", () => {
    const merged = mergeProfileDefaults({
      family: "layer1",
      prevPrefs: {
        goldSource: "curated_gold",
        thresholdProfile: "from_gold",
        userOverrides: { goldSource: false, thresholdProfile: true },
      },
      nextModelProfile: "student_mistral_small_32",
      profile: {
        default_gold_source: "teacher_gold",
        default_threshold_profile: "student_mistral",
      },
    });
    expect(merged.goldSource).toBe("teacher_gold");
    expect(merged.thresholdProfile).toBe("from_gold");
  });
});

describe("buildRunPayload", () => {
  it("builds selected-cases payload with custom model and advanced options", () => {
    expect(
      buildRunPayload({
        family: "layer1",
        caseIds: ["yolov1"],
        launcherScope: "selected",
        label: "selected",
        modelProfile: "custom",
        customModelId: "openrouter/foo",
        goldSource: "teacher_gold",
        thresholdProfile: "student_mistral",
        baseUrlOverride: "https://example.com/v1",
        apiKeyEnvName: "SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY",
      }),
    ).toEqual({
      family: "layer1",
      case_ids: ["yolov1"],
      label: "selected",
      model_profile: "custom",
      model_id: "openrouter/foo",
      gold_source: "teacher_gold",
      threshold_profile: "student_mistral",
      base_url_override: "https://example.com/v1",
      api_key_env_name: "SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY",
    });
  });

  it("maps nightly to nightly_semantic for layer2", () => {
    const payload = buildRunPayload({
      family: "layer2",
      caseIds: [],
      launcherScope: "nightly",
      label: "nightly_semantic",
      modelProfile: "env_default",
    });
    expect(payload.case_ids).toBe("nightly_semantic");
    expect(payload.gold_source).toBe("semantic_gold");
    expect(payload.threshold_profile).toBeUndefined();
  });
});

describe("validateLauncherConfig", () => {
  it("requires custom model id and valid URL/env formats", () => {
    const errors = validateLauncherConfig({
      family: "layer1",
      launcherScope: "selected",
      caseIds: [],
      modelProfile: "custom",
      customModelId: "",
      baseUrlOverride: "notaurl",
      apiKeyEnvName: "bad key",
    });
    expect(errors).toContain("Select at least one case before starting a selected-cases run.");
    expect(errors).toContain("Custom model id is required when the custom profile is selected.");
    expect(errors).toContain("Base URL override must be a valid http(s) URL.");
    expect(errors).toContain("API key env var should look like a single environment variable name.");
  });
});

describe("humanizeLauncherError", () => {
  it("maps backend detail strings to readable UI errors", () => {
    expect(humanizeLauncherError({ response: { data: { detail: "custom_model_id_required" } } })).toBe(
      "Custom profile requires a custom model id.",
    );
    expect(
      humanizeLauncherError({ response: { data: { detail: "gold_source_not_supported_for_family:teacher_gold:layer2" } } }),
    ).toContain("teacher_gold");
  });
});

describe("buildExecutionSummary", () => {
  it("uses effective run config when available", () => {
    const summary = buildExecutionSummary(
      {
        run_id: "r1",
        status: "running",
        benchmark_family: "layer1",
        run_config: {
          model_profile: "student_mistral_small_32",
          resolved_model_id: "mistralai/mistral-small-3.2-24b-instruct",
          gold_source: "teacher_gold",
          threshold_profile: "student_mistral",
        },
      },
      { fallbackScopeLabel: "nightly_heavy" },
    );
    expect(summary.scopeLabel).toBe("nightly_heavy");
    expect(summary.effectiveModelId).toContain("mistral-small");
    expect(summary.goldSource).toBe("teacher_gold");
  });
});
