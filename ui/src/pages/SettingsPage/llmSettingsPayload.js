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
