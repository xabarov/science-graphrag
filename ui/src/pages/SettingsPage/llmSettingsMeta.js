export function advancedFieldLabel(t, key) {
  const i18nKey = `llm.advanced.field.${key}`;
  const label = t(i18nKey);
  return label !== i18nKey ? label : key;
}
