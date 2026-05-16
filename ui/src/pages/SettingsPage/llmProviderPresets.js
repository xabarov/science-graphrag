/** @typedef {"openrouter" | "vllm" | "ollama"} LlmProviderPresetId */

export const OLLAMA_LOCAL_BASE_URL = "http://localhost:11434/v1";
export const OLLAMA_PLACEHOLDER_API_KEY = "ollama";

/**
 * Static preset values (no i18n). Labels come from i18n in the UI card.
 *
 * @typedef {{
 *   baseUrl: string,
 *   model: string,
 *   temperature: string,
 *   timeoutSeconds: string,
 *   apiKey: string,
 *   chatModel: string,
 *   chatBaseUrl: string,
 *   chatTemperature: string,
 *   chatTimeoutSeconds: string,
 *   chatApiKey: string,
 *   vlModel: string,
 *   vlBaseUrl: string,
 *   vlTemperature: string,
 *   vlTimeoutSeconds: string,
 *   visionApiKey: string,
 *   embeddingsBaseUrl: string,
 *   embeddingsModel: string,
 *   embeddingsTimeoutSeconds: string,
 *   embeddingsApiKey: string,
 * }} LlmPresetFormValues
 */

/** @type {Record<LlmProviderPresetId, LlmPresetFormValues>} */
export const LLM_PROVIDER_PRESETS = {
  openrouter: {
    baseUrl: "https://openrouter.ai/api/v1",
    model: "mistralai/mistral-small-3.2-24b-instruct",
    temperature: "0",
    timeoutSeconds: "180",
    apiKey: "",
    chatModel: "",
    chatBaseUrl: "",
    chatTemperature: "0",
    chatTimeoutSeconds: "180",
    chatApiKey: "",
    vlModel: "",
    vlBaseUrl: "",
    vlTemperature: "0",
    vlTimeoutSeconds: "300",
    visionApiKey: "",
    embeddingsBaseUrl: "https://openrouter.ai/api/v1",
    embeddingsModel: "baai/bge-m3",
    embeddingsTimeoutSeconds: "60",
    embeddingsApiKey: "",
  },
  vllm: {
    baseUrl: "",
    model: "",
    temperature: "0",
    timeoutSeconds: "180",
    apiKey: "",
    chatModel: "",
    chatBaseUrl: "",
    chatTemperature: "0",
    chatTimeoutSeconds: "180",
    chatApiKey: "",
    vlModel: "",
    vlBaseUrl: "",
    vlTemperature: "0",
    vlTimeoutSeconds: "300",
    visionApiKey: "",
    embeddingsBaseUrl: "",
    embeddingsModel: "",
    embeddingsTimeoutSeconds: "60",
    embeddingsApiKey: "",
  },
  ollama: {
    baseUrl: OLLAMA_LOCAL_BASE_URL,
    model: "llama3.2",
    temperature: "0",
    timeoutSeconds: "300",
    apiKey: OLLAMA_PLACEHOLDER_API_KEY,
    chatModel: "llama3.2",
    chatBaseUrl: OLLAMA_LOCAL_BASE_URL,
    chatTemperature: "0",
    chatTimeoutSeconds: "300",
    chatApiKey: OLLAMA_PLACEHOLDER_API_KEY,
    vlModel: "llava",
    vlBaseUrl: OLLAMA_LOCAL_BASE_URL,
    vlTemperature: "0",
    vlTimeoutSeconds: "300",
    visionApiKey: OLLAMA_PLACEHOLDER_API_KEY,
    embeddingsBaseUrl: OLLAMA_LOCAL_BASE_URL,
    embeddingsModel: "all-minilm",
    embeddingsTimeoutSeconds: "120",
    embeddingsApiKey: OLLAMA_PLACEHOLDER_API_KEY,
  },
};

/**
 * @param {LlmProviderPresetId} presetId
 * @returns {LlmPresetFormValues}
 */
export function getLlmProviderPreset(presetId) {
  return { ...LLM_PROVIDER_PRESETS[presetId] };
}

/**
 * Detect probable Ollama endpoint from base URL (for hints only).
 *
 * @param {string} baseUrl
 * @returns {boolean}
 */
export function isProbableOllamaBaseUrl(baseUrl) {
  const raw = String(baseUrl || "").trim();
  if (!raw) return false;
  try {
    const url = new URL(raw);
    const path = url.pathname.replace(/\/+$/, "") || "";
    if (path !== "/v1") return false;
    return url.host.includes("11434");
  } catch {
    return false;
  }
}
