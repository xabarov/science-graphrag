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
 *   temperature: number,
 *   timeoutSeconds: number,
 *   vlModel: string,
 *   vlBaseUrl: string,
 *   llm: object,
 *   replaceKey: boolean,
 *   apiKey: string,
 *   replaceVisionKey: boolean,
 *   visionApiKey: string,
 *   advDirty: boolean,
 *   advValues: object,
 * }} opts
 */
export function buildLlmSettingsSubmitPayload(opts) {
  const {
    baseUrl,
    model,
    chatModel,
    temperature,
    timeoutSeconds,
    vlModel,
    vlBaseUrl,
    llm,
    replaceKey,
    apiKey,
    replaceVisionKey,
    visionApiKey,
    advDirty,
    advValues,
  } = opts;

  const persistedVm = (llm?.vl_model || "").trim();
  const persistedVb = (llm?.vl_base_url || "").trim();
  const persistedCm = (llm?.chat_model || "").trim();

  const payload = {
    base_url: baseUrl,
    model,
    temperature: Number(temperature),
    timeout_seconds: Number(timeoutSeconds),
  };

  if (chatModel.trim() !== persistedCm) {
    payload.chat_model = chatModel.trim();
  }
  if (vlModel.trim() !== persistedVm) {
    payload.vl_model = vlModel.trim();
  }
  if (vlBaseUrl.trim() !== persistedVb) {
    payload.vl_base_url = vlBaseUrl.trim();
  }
  if (replaceKey && apiKey) {
    payload.api_key = apiKey;
  }
  if (replaceVisionKey && visionApiKey.trim()) {
    payload.vision_api_key = visionApiKey.trim();
  }
  if (advDirty) {
    payload.runtime_overrides = buildRuntimeOverridesPayload(advValues);
  }
  return payload;
}
