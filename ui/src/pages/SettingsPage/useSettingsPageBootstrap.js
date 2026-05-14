import { useEffect, useState } from "react";
import { getSettingsSchema, getSettingsSnapshot } from "./settingsApi.js";
import { formatResearchApiError } from "../../services/researchApi.js";

/**
 * Loads settings schema/snapshot and resolves the active section from URL `?section=`.
 *
 * @param {{ settingsUrlSearchKey: string, t: (key: string) => string }} params
 */
export function useSettingsPageBootstrap({ settingsUrlSearchKey, t }) {
  const [snapshot, setSnapshot] = useState(null);
  const [schema, setSchema] = useState(null);
  const [activeSectionId, setActiveSectionId] = useState("llm");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true);
      setLoadError("");
      try {
        const [nextSchema, nextSnapshot] = await Promise.all([getSettingsSchema(), getSettingsSnapshot()]);
        if (!mounted) return;
        setSchema(nextSchema);
        setSnapshot(nextSnapshot);
        const sectionIds = new Set((nextSnapshot.sections || []).map((s) => s.id));
        const urlSection = (new URLSearchParams(settingsUrlSearchKey).get("section") || "").trim();
        const fromUrl = urlSection && sectionIds.has(urlSection) ? urlSection : null;
        const fallback = nextSnapshot.sections.some((item) => item.id === "llm")
          ? "llm"
          : nextSnapshot.sections[0]?.id || "llm";
        setActiveSectionId(fromUrl || fallback);
      } catch (error) {
        if (!mounted) return;
        setLoadError(formatResearchApiError(error) || t("settings.page.loadError"));
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, [t, settingsUrlSearchKey]);

  return {
    snapshot,
    setSnapshot,
    schema,
    activeSectionId,
    setActiveSectionId,
    loading,
    loadError,
  };
}
