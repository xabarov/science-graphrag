/** Resolve localized settings nav label/description with API fallback. */
export function resolveSettingsSectionLabel(section, t) {
  const labelKey = `settings.snapshot.${section.id}.label`;
  return t(labelKey) !== labelKey ? t(labelKey) : section.label;
}

export function resolveSettingsSectionDescription(section, t) {
  const descKey = `settings.snapshot.${section.id}.description`;
  return t(descKey) !== descKey ? t(descKey) : section.description;
}
