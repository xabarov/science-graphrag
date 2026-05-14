/** @vitest-environment node */
import { describe, expect, it } from "vitest";

import { deriveAskPanelScopeEyebrow } from "./askPanelScopePresentation.js";

describe("deriveAskPanelScopeEyebrow", () => {
  const t = (key) => key;

  it("prefers workspace scoped when in workspace or locked", () => {
    expect(deriveAskPanelScopeEyebrow(t, { inWorkspace: true, locked: false, corpusWorkspaceOnly: false })).toBe(
      "askPanel.banner.workspaceScoped",
    );
    expect(deriveAskPanelScopeEyebrow(t, { inWorkspace: false, locked: true, corpusWorkspaceOnly: false })).toBe(
      "askPanel.banner.workspaceScoped",
    );
  });

  it("uses corpus title when corpus-only", () => {
    expect(deriveAskPanelScopeEyebrow(t, { inWorkspace: false, locked: false, corpusWorkspaceOnly: true })).toBe(
      "askPanel.banner.workspaceCorpusTitle",
    );
  });

  it("falls back to standalone", () => {
    expect(deriveAskPanelScopeEyebrow(t, { inWorkspace: false, locked: false, corpusWorkspaceOnly: false })).toBe(
      "askPanel.banner.standalone",
    );
  });
});
