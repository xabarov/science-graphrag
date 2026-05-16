/** @typedef {"openrouter" | "vllm" | "ollama"} LlmGlobalPresetId */
/** @typedef {"extraction" | "chat" | "vision" | "embeddings"} LlmTaskId */

export const OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1";
export const OLLAMA_LOCAL_BASE_URL = "http://localhost:11434/v1";
export const OLLAMA_PLACEHOLDER_API_KEY = "ollama";

const OPENROUTER_CHAT_MODEL = "mistralai/mistral-small-3.2-24b-instruct";
const OPENROUTER_VISION_MODEL = "qwen/qwen3-vl-235b-a22b-instruct";
const OLLAMA_CHAT_MODEL = "gemma4";
const OLLAMA_VISION_MODEL = "llava";

/**
 * Full form shape used by bulk apply (union of all task fields).
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

/** @typedef {Partial<LlmPresetFormValues>} LlmPresetFormPatch */

/** @typedef {{ id: string, patch: LlmPresetFormPatch }} LlmTaskPresetAction */

/** @type {Record<LlmTaskId, Record<string, LlmPresetFormPatch>>} */
export const LLM_TASK_PRESET_PATCHES = {
  extraction: {
    openrouter: {
      baseUrl: OPENROUTER_BASE_URL,
      model: OPENROUTER_CHAT_MODEL,
      temperature: "0",
      timeoutSeconds: "180",
      apiKey: "",
    },
    ollama: {
      baseUrl: OLLAMA_LOCAL_BASE_URL,
      model: OLLAMA_CHAT_MODEL,
      temperature: "0",
      timeoutSeconds: "300",
      apiKey: OLLAMA_PLACEHOLDER_API_KEY,
    },
    vllm: {
      baseUrl: "",
      model: "",
      temperature: "0",
      timeoutSeconds: "180",
      apiKey: "",
    },
  },
  chat: {
    inherit_extraction: {
      chatModel: "",
      chatBaseUrl: "",
      chatTemperature: "0",
      chatTimeoutSeconds: "180",
      chatApiKey: "",
    },
    openrouter: {
      chatModel: OPENROUTER_CHAT_MODEL,
      chatBaseUrl: OPENROUTER_BASE_URL,
      chatTemperature: "0",
      chatTimeoutSeconds: "180",
      chatApiKey: "",
    },
    ollama: {
      chatModel: OLLAMA_CHAT_MODEL,
      chatBaseUrl: OLLAMA_LOCAL_BASE_URL,
      chatTemperature: "0",
      chatTimeoutSeconds: "300",
      chatApiKey: OLLAMA_PLACEHOLDER_API_KEY,
    },
    vllm: {
      chatModel: "",
      chatBaseUrl: "",
      chatTemperature: "0",
      chatTimeoutSeconds: "180",
      chatApiKey: "",
    },
  },
  vision: {
    inherit_extraction: {
      vlModel: "",
      vlBaseUrl: "",
      vlTemperature: "0",
      vlTimeoutSeconds: "300",
      visionApiKey: "",
    },
    openrouter_vision: {
      vlModel: OPENROUTER_VISION_MODEL,
      vlBaseUrl: OPENROUTER_BASE_URL,
      vlTemperature: "0",
      vlTimeoutSeconds: "300",
      visionApiKey: "",
    },
    ollama_vision: {
      vlModel: OLLAMA_VISION_MODEL,
      vlBaseUrl: OLLAMA_LOCAL_BASE_URL,
      vlTemperature: "0",
      vlTimeoutSeconds: "300",
      visionApiKey: OLLAMA_PLACEHOLDER_API_KEY,
    },
    manual: {
      vlModel: "",
      vlBaseUrl: "",
      vlTemperature: "0",
      vlTimeoutSeconds: "300",
      visionApiKey: "",
    },
  },
  embeddings: {
    openrouter_bge: {
      embeddingsBaseUrl: OPENROUTER_BASE_URL,
      embeddingsModel: "baai/bge-m3",
      embeddingsTimeoutSeconds: "60",
      embeddingsApiKey: "",
    },
    ollama_qwen: {
      embeddingsBaseUrl: OLLAMA_LOCAL_BASE_URL,
      embeddingsModel: "qwen3-embedding:0.6b",
      embeddingsTimeoutSeconds: "120",
      embeddingsApiKey: OLLAMA_PLACEHOLDER_API_KEY,
    },
    ollama_minilm: {
      embeddingsBaseUrl: OLLAMA_LOCAL_BASE_URL,
      embeddingsModel: "all-minilm",
      embeddingsTimeoutSeconds: "120",
      embeddingsApiKey: OLLAMA_PLACEHOLDER_API_KEY,
    },
    manual: {
      embeddingsBaseUrl: "",
      embeddingsModel: "",
      embeddingsTimeoutSeconds: "60",
      embeddingsApiKey: "",
    },
  },
};

/** @type {Record<LlmTaskId, string[]>} */
export const LLM_TASK_PRESET_ACTION_ORDER = {
  extraction: ["openrouter", "ollama", "vllm"],
  chat: ["inherit_extraction", "openrouter", "ollama", "vllm"],
  vision: ["inherit_extraction", "openrouter_vision", "ollama_vision", "manual"],
  embeddings: ["openrouter_bge", "ollama_qwen", "ollama_minilm", "manual"],
};

/**
 * @param {LlmTaskId} task
 * @param {string} actionId
 * @returns {LlmPresetFormPatch}
 */
export function getTaskPresetPatch(task, actionId) {
  const bucket = LLM_TASK_PRESET_PATCHES[task];
  const patch = bucket?.[actionId];
  if (!patch) {
    throw new Error(`Unknown task preset: ${task}/${actionId}`);
  }
  return { ...patch };
}

/**
 * Merge task patches into a full form values object (later keys win).
 *
 * @param {LlmPresetFormPatch[]} patches
 * @returns {LlmPresetFormValues}
 */
export function mergePresetPatches(patches) {
  /** @type {LlmPresetFormValues} */
  const empty = {
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
  };
  return patches.reduce((acc, patch) => ({ ...acc, ...patch }), empty);
}

/**
 * @param {LlmGlobalPresetId} presetId
 * @returns {LlmPresetFormValues}
 */
export function getLlmProviderPreset(presetId) {
  const byTask = {
    openrouter: ["extraction", "chat", "vision", "embeddings"].map((task) => {
      const actionId =
        task === "extraction"
          ? "openrouter"
          : task === "chat"
            ? "openrouter"
            : task === "vision"
              ? "openrouter_vision"
              : "openrouter_bge";
      return getTaskPresetPatch(task, actionId);
    }),
    ollama: ["extraction", "chat", "vision", "embeddings"].map((task) => {
      const actionId =
        task === "extraction"
          ? "ollama"
          : task === "chat"
            ? "ollama"
            : task === "vision"
              ? "ollama_vision"
              : "ollama_qwen";
      return getTaskPresetPatch(task, actionId);
    }),
    vllm: ["extraction", "chat", "vision", "embeddings"].map((task) => {
      const actionId =
        task === "extraction"
          ? "vllm"
          : task === "chat"
            ? "vllm"
            : task === "vision"
              ? "manual"
              : "manual";
      return getTaskPresetPatch(task, actionId);
    }),
  };
  return mergePresetPatches(byTask[presetId] || []);
}

/** @deprecated Use getLlmProviderPreset; kept for imports. */
export const LLM_PROVIDER_PRESETS = {
  openrouter: getLlmProviderPreset("openrouter"),
  vllm: getLlmProviderPreset("vllm"),
  ollama: getLlmProviderPreset("ollama"),
};

/**
 * @param {LlmTaskId} task
 * @returns {LlmTaskPresetAction[]}
 */
export function listTaskPresetActions(task) {
  const order = LLM_TASK_PRESET_ACTION_ORDER[task] || [];
  return order.map((id) => ({
    id,
    patch: getTaskPresetPatch(task, id),
  }));
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
