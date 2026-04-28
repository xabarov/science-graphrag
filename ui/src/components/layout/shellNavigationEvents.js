export const SHELL_NAVIGATION_INTENT_EVENT = "science-graphrag:shell-navigation-intent";

export function dispatchShellNavigationIntent(target) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent(SHELL_NAVIGATION_INTENT_EVENT, {
      detail: { target: String(target || "") },
    }),
  );
}
