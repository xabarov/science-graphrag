export function advancedFieldLabel(t, key) {
  const i18nKey = `llm.advanced.field.${key}`;
  const label = t(i18nKey);
  return label !== i18nKey ? label : key;
}

export function providerSummary(llm, t) {
  const bits = [];
  const configured = llm?.status?.configured;
  const src = llm?.status?.secret_source;
  if (configured) {
    if (src === "server_managed") bits.push(t("llm.summary.sourceServer"));
    else if (src === "environment") bits.push(t("llm.summary.sourceEnv"));
    else bits.push(t("llm.summary.hasCredential"));
  } else {
    bits.push(t("llm.summary.noCredential"));
  }
  if (llm?.effective?.resolved_model) {
    bits.push(t("llm.summary.model", { model: llm.effective.resolved_model }));
  }
  if (llm?.effective?.resolved_chat_model) {
    bits.push(t("llm.summary.chatModel", { model: llm.effective.resolved_chat_model }));
  }
  if (llm?.effective?.resolved_base_url) {
    bits.push(llm.effective.resolved_base_url);
  }
  return bits.filter(Boolean).join(" • ");
}

export function credentialAlertSeverity(secretSource, configured) {
  if (!configured) return "warning";
  if (secretSource === "environment") return "info";
  return "success";
}

export function credentialAlertBody(llm, t) {
  const st = llm?.status || {};
  const configured = st.configured;
  const src = st.secret_source;
  const masked = st.masked_key;
  const maskedSuffix = masked ? ` (${masked})` : "";

  if (!configured) {
    return { primary: t("llm.credentials.none"), hint: null };
  }
  if (src === "environment") {
    return {
      primary: t("llm.credentials.fromEnv", { masked: maskedSuffix }),
      hint: st.env_key_hint || null,
    };
  }
  return {
    primary: t("llm.credentials.fromServer", { masked: maskedSuffix }),
    hint: null,
  };
}
