import { describe, expect, it } from "vitest";

import {
  OLLAMA_LOCAL_BASE_URL,
  OLLAMA_PLACEHOLDER_API_KEY,
  getLlmProviderPreset,
  isProbableOllamaBaseUrl,
} from "./llmProviderPresets.js";
import { buildLlmSettingsSubmitPayload } from "./llmSettingsPayload.js";

describe("llmProviderPresets", () => {
  it("ollama preset uses local OpenAI-compatible endpoint and placeholder key", () => {
    const p = getLlmProviderPreset("ollama");
    expect(p.baseUrl).toBe(OLLAMA_LOCAL_BASE_URL);
    expect(p.apiKey).toBe(OLLAMA_PLACEHOLDER_API_KEY);
    expect(p.embeddingsModel).toBe("all-minilm");
    expect(p.embeddingsBaseUrl).toBe(OLLAMA_LOCAL_BASE_URL);
  });

  it("detects probable Ollama base URL", () => {
    expect(isProbableOllamaBaseUrl("http://localhost:11434/v1")).toBe(true);
    expect(isProbableOllamaBaseUrl("http://127.0.0.1:11434/v1/")).toBe(true);
    expect(isProbableOllamaBaseUrl("https://openrouter.ai/api/v1")).toBe(false);
    expect(isProbableOllamaBaseUrl("http://localhost:11434/api/v1")).toBe(false);
  });

  it("ollama preset submit payload uses canonical tasks and task api keys", () => {
    const p = getLlmProviderPreset("ollama");
    const body = buildLlmSettingsSubmitPayload({
      baseUrl: p.baseUrl,
      model: p.model,
      chatModel: p.chatModel,
      chatBaseUrl: p.chatBaseUrl,
      temperature: Number(p.temperature),
      timeoutSeconds: Number(p.timeoutSeconds),
      vlModel: p.vlModel,
      vlBaseUrl: p.vlBaseUrl,
      vlTemperature: Number(p.vlTemperature),
      vlTimeoutSeconds: Number(p.vlTimeoutSeconds),
      apiKey: p.apiKey,
      chatApiKey: p.chatApiKey,
      visionApiKey: p.visionApiKey,
      chatTemperature: Number(p.chatTemperature),
      chatTimeoutSeconds: Number(p.chatTimeoutSeconds),
      embeddingsBaseUrl: p.embeddingsBaseUrl,
      embeddingsModel: p.embeddingsModel,
      embeddingsTimeoutSeconds: Number(p.embeddingsTimeoutSeconds),
      embeddingsApiKey: p.embeddingsApiKey,
      advDirty: false,
      advValues: {},
    });
    expect(body.tasks.extraction.base_url).toBe(OLLAMA_LOCAL_BASE_URL);
    expect(body.tasks.embeddings.model).toBe("all-minilm");
    expect(body.api_key).toBe("ollama");
    expect(body.embeddings_api_key).toBe("ollama");
    expect(body).not.toHaveProperty("embeddings_mode");
  });
});
