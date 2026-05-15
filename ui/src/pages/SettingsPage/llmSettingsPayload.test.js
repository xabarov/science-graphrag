import { describe, expect, it } from "vitest";

import { buildLlmSettingsSubmitPayload } from "./llmSettingsPayload.js";

describe("buildLlmSettingsSubmitPayload", () => {
  const baseLlm = {
    base_url: "https://openrouter.ai/api/v1",
    model: "m-base",
    chat_model: "",
    vl_model: "",
    vl_base_url: "",
    effective: {
      resolved_vl_model: "qwen/vl-default",
      resolved_vl_base_url: "https://openrouter.ai/api/v1",
      resolved_timeout_seconds: 180,
    },
  };

  it("omits vl_model and vl_base_url when unchanged from persisted (no phantom override)", () => {
    const p = buildLlmSettingsSubmitPayload({
      baseUrl: baseLlm.base_url,
      model: baseLlm.model,
      chatModel: "",
      temperature: 0,
      timeoutSeconds: 120,
      vlModel: "",
      vlBaseUrl: "",
      llm: baseLlm,
      replaceKey: false,
      apiKey: "",
      replaceVisionKey: false,
      visionApiKey: "",
      advDirty: false,
      advValues: {},
    });
    expect(p).not.toHaveProperty("vl_model");
    expect(p).not.toHaveProperty("vl_base_url");
    expect(p.timeout_seconds).toBe(120);
  });

  it("includes vl_model when user overrides persisted empty", () => {
    const p = buildLlmSettingsSubmitPayload({
      baseUrl: baseLlm.base_url,
      model: baseLlm.model,
      chatModel: "",
      temperature: 0,
      timeoutSeconds: 180,
      vlModel: "custom/vl",
      vlBaseUrl: "",
      llm: baseLlm,
      replaceKey: false,
      apiKey: "",
      replaceVisionKey: false,
      visionApiKey: "",
      advDirty: false,
      advValues: {},
    });
    expect(p.vl_model).toBe("custom/vl");
    expect(p).not.toHaveProperty("vl_base_url");
  });

  it("sends empty vl_model to clear persisted override", () => {
    const llm = { ...baseLlm, vl_model: "old/vl" };
    const p = buildLlmSettingsSubmitPayload({
      baseUrl: llm.base_url,
      model: llm.model,
      chatModel: "",
      temperature: 0,
      timeoutSeconds: 180,
      vlModel: "",
      vlBaseUrl: "",
      llm,
      replaceKey: false,
      apiKey: "",
      replaceVisionKey: false,
      visionApiKey: "",
      advDirty: false,
      advValues: {},
    });
    expect(p.vl_model).toBe("");
  });
});
