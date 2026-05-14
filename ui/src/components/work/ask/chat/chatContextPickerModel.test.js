/** @vitest-environment node */
import { describe, expect, it } from "vitest";

import { deriveChatContextSummaryLabel } from "./chatContextPickerModel.js";

describe("deriveChatContextSummaryLabel", () => {
  const t = (key) => key;

  it("uses whole workspace when corpus-only with workspace id", () => {
    expect(
      deriveChatContextSummaryLabel(
        { workId: "", resolvedWork: null, corpusWorkspaceOnly: true, standaloneMode: false, workspaceId: "ws-1" },
        t,
      ),
    ).toBe("chat.context.wholeWorkspace");
  });

  it("uses global corpus in standalone mode", () => {
    expect(
      deriveChatContextSummaryLabel(
        { workId: "", resolvedWork: null, corpusWorkspaceOnly: false, standaloneMode: true, workspaceId: "" },
        t,
      ),
    ).toBe("chat.context.globalCorpus");
  });

  it("uses not set when no work and not corpus/standalone", () => {
    expect(
      deriveChatContextSummaryLabel(
        { workId: "", resolvedWork: null, corpusWorkspaceOnly: false, standaloneMode: false, workspaceId: "" },
        t,
      ),
    ).toBe("chat.context.notSet");
  });
});
