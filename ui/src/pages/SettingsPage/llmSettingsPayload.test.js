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
    tasks: {
      extraction: {
        base_url: "https://openrouter.ai/api/v1",
        model: "m-base",
        temperature: 0,
        timeout_seconds: 180,
      },
      chat: {
        base_url: "",
        model: "",
        temperature: 0,
        timeout_seconds: 180,
      },
      vision: {
        base_url: "",
        model: "",
        temperature: 0,
        timeout_seconds: 300,
      },
      embeddings: {
        mode: "http",
        base_url: "https://openrouter.ai/api/v1",
        model: "baai/bge-m3",
        timeout_seconds: 60,
      },
    },
  };

  it("builds canonical nested task payload", () => {
    const p = buildLlmSettingsSubmitPayload({
      baseUrl: baseLlm.base_url,
      model: baseLlm.model,
      chatModel: "",
      chatBaseUrl: "",
      chatTemperature: 0,
      chatTimeoutSeconds: 180,
      temperature: 0,
      timeoutSeconds: 120,
      vlModel: "",
      vlBaseUrl: "",
      vlTemperature: 0,
      vlTimeoutSeconds: 300,
      llm: baseLlm,
      apiKey: "",
      chatApiKey: "",
      visionApiKey: "",
      embeddingsBaseUrl: "https://embed.example/v1",
      embeddingsModel: "baai/bge-m3",
      embeddingsTimeoutSeconds: 60,
      embeddingsApiKey: "",
      advDirty: false,
      advValues: {},
    });
    expect(p).not.toHaveProperty("base_url");
    expect(p.tasks.extraction.timeout_seconds).toBe(120);
    expect(p.tasks.embeddings).toEqual({
      mode: "http",
      base_url: "https://embed.example/v1",
      model: "baai/bge-m3",
      timeout_seconds: 60,
    });
  });

  it("includes per-task chat and vision temperature/timeouts", () => {
    const p = buildLlmSettingsSubmitPayload({
      baseUrl: baseLlm.base_url,
      model: baseLlm.model,
      chatModel: "chat-x",
      chatBaseUrl: "",
      chatTemperature: 0.2,
      chatTimeoutSeconds: 90,
      temperature: 0,
      timeoutSeconds: 180,
      vlModel: "custom/vl",
      vlBaseUrl: "",
      vlTemperature: 0.1,
      vlTimeoutSeconds: 240,
      llm: baseLlm,
      apiKey: "",
      chatApiKey: "",
      visionApiKey: "",
      embeddingsBaseUrl: "https://openrouter.ai/api/v1",
      embeddingsModel: "baai/bge-m3",
      embeddingsTimeoutSeconds: 60,
      embeddingsApiKey: "",
      advDirty: false,
      advValues: {},
    });
    expect(p.tasks.chat).toMatchObject({ model: "chat-x", temperature: 0.2, timeout_seconds: 90 });
    expect(p.tasks.vision).toMatchObject({ model: "custom/vl", temperature: 0.1, timeout_seconds: 240 });
  });

  it("includes api_key when draft key is non-empty", () => {
    const p = buildLlmSettingsSubmitPayload({
      baseUrl: baseLlm.base_url,
      model: baseLlm.model,
      chatModel: "",
      chatBaseUrl: "",
      chatTemperature: 0,
      chatTimeoutSeconds: 180,
      temperature: 0,
      timeoutSeconds: 180,
      vlModel: "",
      vlBaseUrl: "",
      vlTemperature: 0,
      vlTimeoutSeconds: 300,
      llm: baseLlm,
      apiKey: "  sk-test  ",
      chatApiKey: "",
      visionApiKey: "",
      embeddingsBaseUrl: "https://openrouter.ai/api/v1",
      embeddingsModel: "baai/bge-m3",
      embeddingsTimeoutSeconds: 60,
      embeddingsApiKey: "",
      advDirty: false,
      advValues: {},
    });
    expect(p.api_key).toBe("sk-test");
  });

  it("includes independent chat and embeddings fields", () => {
    const p = buildLlmSettingsSubmitPayload({
      baseUrl: baseLlm.base_url,
      model: baseLlm.model,
      chatModel: "chat-x",
      chatBaseUrl: "https://chat.example/v1",
      chatTemperature: 0,
      chatTimeoutSeconds: 180,
      temperature: 0,
      timeoutSeconds: 180,
      vlModel: "",
      vlBaseUrl: "",
      vlTemperature: 0,
      vlTimeoutSeconds: 300,
      llm: { ...baseLlm, embeddings_mode: "openrouter", embeddings_model: "" },
      apiKey: "",
      chatApiKey: " sk-chat ",
      visionApiKey: "",
      embeddingsBaseUrl: "https://embed.example/v1",
      embeddingsModel: "all-MiniLM-L6-v2",
      embeddingsTimeoutSeconds: 30,
      embeddingsApiKey: " sk-emb ",
      advDirty: false,
      advValues: {},
    });
    expect(p.tasks.chat.base_url).toBe("https://chat.example/v1");
    expect(p.chat_api_key).toBe("sk-chat");
    expect(p.tasks.embeddings.mode).toBe("http");
    expect(p.tasks.embeddings.base_url).toBe("https://embed.example/v1");
    expect(p.tasks.embeddings.model).toBe("all-MiniLM-L6-v2");
    expect(p.tasks.embeddings.timeout_seconds).toBe(30);
    expect(p.embeddings_api_key).toBe("sk-emb");
  });
});
