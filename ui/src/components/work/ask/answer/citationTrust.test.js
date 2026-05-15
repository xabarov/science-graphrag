import { describe, expect, it } from "vitest";

import { buildCitationTrustBadges, citationTrustFallbackI18nKey, coalesceExternalFlag, formatCitationTrustFallbackText } from "./citationTrust.js";

describe("citationTrust", () => {
  it("coerces string is_external from API", () => {
    expect(coalesceExternalFlag("true")).toBe(true);
    expect(coalesceExternalFlag("false")).toBe(false);
    expect(coalesceExternalFlag(undefined)).toBe(false);
  });

  it("builds detailed badges for external web summary", () => {
    const badges = buildCitationTrustBadges(
      {
        is_external: true,
        evidence_mode: "web_summary",
        provenance_kind: "web_page_summary",
      },
      "detailed",
    );
    const ids = badges.map((b) => b.id);
    expect(ids).toContain("external");
    expect(ids).toContain("webSummary");
  });

  it("shows OpenAlex metadata chip without redundant weak quality chip", () => {
    const badges = buildCitationTrustBadges(
      {
        is_external: true,
        evidence_mode: "metadata_only",
        provenance_kind: "openalex_metadata",
        evidence_quality: "weak",
      },
      "detailed",
    );
    const ids = badges.map((b) => b.id);
    expect(ids).toContain("openAlexMeta");
    expect(ids.some((x) => x.startsWith("quality_"))).toBe(false);
  });

  it("still shows quality chip for OpenAlex when quality is not weak", () => {
    const badges = buildCitationTrustBadges(
      {
        is_external: true,
        evidence_mode: "metadata_only",
        provenance_kind: "openalex_metadata",
        evidence_quality: "medium",
      },
      "detailed",
    );
    const ids = badges.map((b) => b.id);
    expect(ids).toContain("openAlexMeta");
    expect(ids).toContain("quality_medium");
  });

  it("does not add quality chip in simple mode", () => {
    const badges = buildCitationTrustBadges(
      {
        is_external: true,
        evidence_mode: "abstract",
        provenance_kind: "arxiv_abstract",
      },
      "simple",
    );
    expect(badges.length).toBeLessThanOrEqual(2);
    expect(badges[0].id).toBe("external");
  });

  it("formats fallback via i18n when key exists", () => {
    const t = (key) => (key === "askPanel.citation.fallback.host_not_allowed" ? "blocked" : key);
    const out = formatCitationTrustFallbackText(t, { fallback_reason: "host_not_allowed" });
    expect(out).toBe("blocked");
  });

  it("falls back to humanized reason when i18n and message missing", () => {
    const t = (key) => key;
    const out = formatCitationTrustFallbackText(t, { fallback_reason: "host_not_allowed" });
    expect(out).toBe("host not allowed");
  });

  it("maps fallback reason to i18n key", () => {
    expect(citationTrustFallbackI18nKey("rate_limited")).toBe("askPanel.citation.fallback.rate_limited");
  });
});
