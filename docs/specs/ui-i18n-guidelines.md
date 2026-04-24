# UI i18n (EN/RU) — guidelines

## Scope

- **Client-only** language preference: `localStorage` (see `I18N_STORAGE_KEY` in `ui/src/i18n/constants.js`).
- **Runtime switch**: no full page reload; `document.documentElement.lang` follows the active locale.
- **User-facing copy** in `ui/src` goes through dictionaries, not hardcoded JSX strings (technical identifiers, API field names, and log-only strings may stay as-is).

## Structure

- **Provider**: `I18nProvider` in `ui/src/main.jsx` wraps the app tree.
- **Hook**: `useI18n()` from `ui/src/i18n/I18nContext.jsx` → `{ locale, setLocale, t, intlLocale }`.
- **Messages**: merged flat `Record<string, string>` per locale under `ui/src/i18n/messages/{en,ru}/` (split into `part*.js` modules re-exported from `index.js`).
- **Interpolation**: `t("some.key", { var: "value" })` replaces `{{var}}` in the template string.

## Key naming

- Prefer **dot-separated** namespaces: `screen.section.element` (e.g. `askPanel.session.title`, `workspace.upload.chooseFile`).
- Keep **EN and RU files in sync**: every key in `en` should exist in `ru` (and vice versa) to avoid mixed-language UI.

## Fallback policy

- Missing key: `translate()` returns the **key string** (devs should notice quickly). Add the key to both locales when introducing UI.
- Prefer **short, stable keys** over English sentences as keys.

## Intl (dates / numbers / sorting)

- Use `intlLocale` from `useI18n()` for `Intl.DateTimeFormat`, `Intl.NumberFormat`, and `localeCompare` where user-visible ordering matters.
- For non-React modules, use `getRuntimeIntlLocale()` from `ui/src/i18n/runtimeIntlLocale.js` (kept in sync when locale changes).

## Definition of Done (new UI)

1. No new user-visible English/Russian literals in JSX—only `t("…")` (or shared components that already call `t`).
2. Keys added to **both** `en` and `ru` message parts.
3. `cd ui && npm run lint` passes.

## Optional later phase

- Persist language preference on the server (user profile) — not part of the current client-only design.
