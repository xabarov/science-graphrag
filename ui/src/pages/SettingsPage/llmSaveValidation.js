import { LLM_RUNTIME_OVERRIDE_KEYS } from "./llmRuntimeOverrideKeys.js";

/** Provider transport + advanced numeric and cross-field rules (Phase 3). */
export function computeSaveBlockingMessage(t, advValues, timeoutSeconds) {
  const transport = Number(timeoutSeconds);
  if (!Number.isFinite(transport) || transport < 1) {
    return t("llm.field.error.invalidTimeout");
  }
  for (const k of LLM_RUNTIME_OVERRIDE_KEYS) {
    if (
      k === "agent_turn_policy_llm_enabled" ||
      k === "agent_runtime" ||
      k === "llm_distributed_quota_enabled" ||
      k === "llm_distributed_quota_key_prefix"
    )
      continue;
    if (!(k in advValues)) continue;
    const raw = advValues[k];
    if (String(raw).trim() === "") {
      return t("llm.advanced.error.emptyNumeric");
    }
    const num = Number(raw);
    if (!Number.isFinite(num)) {
      return t("llm.advanced.error.invalidNumeric");
    }
  }
  const classifier = Number(advValues.agent_turn_policy_classifier_timeout_seconds);
  const step = Number(advValues.agent_step_timeout_seconds);
  if (Number.isFinite(classifier) && Number.isFinite(transport) && classifier > transport) {
    return t("llm.advanced.error.classifierGtTransport");
  }
  if (Number.isFinite(classifier) && Number.isFinite(step) && step < classifier) {
    return t("llm.advanced.error.stepLtClassifier");
  }
  const distOn =
    advValues.llm_distributed_quota_enabled === "1" || advValues.llm_distributed_quota_enabled === "true";
  if (distOn) {
    const pfx = String(advValues.llm_distributed_quota_key_prefix ?? "").trim();
    if (!pfx) {
      return t("llm.advanced.error.distributedPrefixRequired");
    }
  }
  return "";
}
