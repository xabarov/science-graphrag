import { describe, expect, it } from "vitest";

import { mergeQuoteCandidatesIntoCitations } from "./citationHydration.js";

describe("mergeQuoteCandidatesIntoCitations", () => {
  it("fills excerpt from quote_candidates chunk_id (paper_quote_search shape)", () => {
    const citations = [{ work_id: "w1", chunk_fingerprint: "fp-a", title: "T" }];
    const quoteCandidates = [{ work_id: "w1", chunk_id: "fp-a", quote_text: "Passage body." }];
    const out = mergeQuoteCandidatesIntoCitations(citations, quoteCandidates);
    expect(out[0].excerpt).toBe("Passage body.");
  });

  it("does not overwrite existing excerpt", () => {
    const citations = [{ work_id: "w1", chunk_fingerprint: "fp-a", excerpt: "Keep" }];
    const quoteCandidates = [{ work_id: "w1", chunk_id: "fp-a", quote_text: "Other" }];
    const out = mergeQuoteCandidatesIntoCitations(citations, quoteCandidates);
    expect(out[0].excerpt).toBe("Keep");
  });

  it("injects title from inventory when citation has work_id only", () => {
    const citations = [{ work_id: "w-det" }];
    const inventory = {
      papers: [{ work_id: "w-det", title: "Detection Paper Title" }],
    };
    const out = mergeQuoteCandidatesIntoCitations(citations, [], inventory);
    expect(out[0].title).toBe("Detection Paper Title");
  });

  it("injects title from inventory work_title field on paper row", () => {
    const citations = [{ work_id: "w-x" }];
    const inventory = {
      paper_matches: [{ work_id: "w-x", work_title: "From work_title field" }],
    };
    const out = mergeQuoteCandidatesIntoCitations(citations, [], inventory);
    expect(out[0].title).toBe("From work_title field");
  });

  it("injects work_id from inventory when citation is title-only", () => {
    const citations = [{ title: "My Paper Title" }];
    const quoteCandidates = [{ work_id: "wx", chunk_id: "fp-z", quote_text: "Snippet." }];
    const inventory = { paper_matches: [{ work_id: "wx", title: "My Paper Title" }] };
    const out = mergeQuoteCandidatesIntoCitations(citations, quoteCandidates, inventory);
    expect(out[0].work_id).toBe("wx");
    expect(out[0].excerpt).toBe("Snippet.");
  });
});
