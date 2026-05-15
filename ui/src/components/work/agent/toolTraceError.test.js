import { describe, expect, it } from "vitest";

import { formatToolTraceErrorLine, toolTraceErrorToFallbackReason } from "./toolTraceError.js";

describe("toolTraceError", () => {
  it("maps OpenAlex and DOI parse errors to fallback reasons", () => {
    expect(toolTraceErrorToFallbackReason("openalex_works_search_failed")).toBe("source_unreachable");
    expect(toolTraceErrorToFallbackReason("doi_parse_failed")).toBe("metadata_only_fallback");
    expect(toolTraceErrorToFallbackReason("invalid_doi")).toBe("metadata_only_fallback");
  });

  it("localizes mixed-case error codes via lowercase i18n keys", () => {
    const t = (key) => (key === "askPanel.citation.fallback.host_not_allowed" ? "blocked" : key);
    expect(formatToolTraceErrorLine(t, "Host_Not_Allowed")).toBe("blocked");
  });
});
