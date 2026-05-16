import { LLM_RUNTIME_OVERRIDE_KEYS } from "./llmRuntimeOverrideKeys.js";

export function buildAdvValuesFromLlm(llm) {
  const ac = llm?.advanced_controls;
  const o = {};
  if (!ac) return o;
  for (const k of LLM_RUNTIME_OVERRIDE_KEYS) {
    const cell = ac[k];
    if (!cell) continue;
    if (k === "agent_turn_policy_llm_enabled" || k === "llm_distributed_quota_enabled") {
      o[k] = cell.effective ? "1" : "0";
    } else {
      o[k] = String(cell.effective);
    }
  }
  return o;
}

export function buildRuntimeOverridesPayload(advValues) {
  const o = {};
  for (const k of LLM_RUNTIME_OVERRIDE_KEYS) {
    if (!(k in advValues)) continue;
    const raw = advValues[k];
    if (k === "agent_turn_policy_llm_enabled" || k === "llm_distributed_quota_enabled") {
      o[k] = raw === "1" || raw === "true" || raw === true;
      continue;
    }
    if (k === "llm_distributed_quota_key_prefix") {
      o[k] = String(raw || "").trim();
      continue;
    }
    if (k === "agent_runtime") {
      o[k] = String(raw || "").trim();
      continue;
    }
    if (
      k === "agent_step_timeout_seconds" ||
      k === "agent_turn_policy_classifier_timeout_seconds" ||
      k === "work_dedup_llm_timeout_s" ||
      k === "author_dedup_llm_timeout_s" ||
      k === "llm_distributed_quota_acquire_timeout_seconds"
    ) {
      const n = Number(raw);
      if (!Number.isFinite(n)) continue;
      o[k] = n;
    } else {
      const n = parseInt(String(raw), 10);
      if (!Number.isFinite(n)) continue;
      o[k] = n;
    }
  }
  return o;
}

/**
 * Build PATCH /v1/settings/llm body. VL / chat overrides are included only when they
 * differ from persisted snapshot values so unrelated saves do not materialize inherited defaults.
 *
 * @param {{
 *   baseUrl: string,
 *   model: string,
 *   chatModel: string,
 *   chatBaseUrl: string,
 *   temperature: number,
 *   timeoutSeconds: number,
 *   vlModel: string,
 *   vlBaseUrl: string,
 *   vlTemperature: number,
 *   vlTimeoutSeconds: number,
 *   apiKey: string,
 *   chatApiKey: string,
 *   visionApiKey: string,
 *   chatTemperature: number,
 *   chatTimeoutSeconds: number,
 *   embeddingsBaseUrl: string,
 *   embeddingsModel: string,
 *   embeddingsTimeoutSeconds: number,
 *   embeddingsApiKey: string,
 *   advDirty: boolean,
 *   advValues: object,
 * }} opts
 */
export function buildLlmSettingsSubmitPayload(opts) {
  const {
    baseUrl,
    model,
    chatModel,
    chatBaseUrl,
    temperature,
    timeoutSeconds,
    vlModel,
    vlBaseUrl,
    vlTemperature,
    vlTimeoutSeconds,
    apiKey,
    chatApiKey,
    visionApiKey,
    chatTemperature,
    chatTimeoutSeconds,
    embeddingsBaseUrl,
    embeddingsModel,
    embeddingsTimeoutSeconds,
    embeddingsApiKey,
    advDirty,
    advValues,
  } = opts;

  const payload = {
    tasks: {
      extraction: {
        base_url: baseUrl.trim(),
        model: model.trim(),
        temperature: Number(temperature),
        timeout_seconds: Number(timeoutSeconds),
      },
      chat: {
        base_url: chatBaseUrl.trim(),
        model: chatModel.trim(),
        temperature: Number(chatTemperature),
        timeout_seconds: Number(chatTimeoutSeconds),
      },
      vision: {
        base_url: vlBaseUrl.trim(),
        model: vlModel.trim(),
        temperature: Number(vlTemperature),
        timeout_seconds: Number(vlTimeoutSeconds),
      },
      embeddings: {
        mode: "http",
        base_url: embeddingsBaseUrl.trim(),
        model: embeddingsModel.trim(),
        timeout_seconds: Number(embeddingsTimeoutSeconds),
      },
    },
  };

  if (apiKey.trim()) {
    payload.api_key = apiKey.trim();
  }
  if (chatApiKey.trim()) {
    payload.chat_api_key = chatApiKey.trim();
  }
  if (visionApiKey.trim()) {
    payload.vision_api_key = visionApiKey.trim();
  }
  if (embeddingsApiKey.trim()) {
    payload.embeddings_api_key = embeddingsApiKey.trim();
  }
  if (advDirty) {
    payload.runtime_overrides = buildRuntimeOverridesPayload(advValues);
  }
  return payload;
}
