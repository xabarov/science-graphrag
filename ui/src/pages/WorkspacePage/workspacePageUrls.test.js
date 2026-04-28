import { describe, expect, it } from "vitest";

import { buildStandaloneChatPath, buildStandaloneTracePath } from "../../routing/index.js";
import { GRAPH_PATH, READER_PATH } from "../../routes/paths.js";
import { workChatUrl, workGraphUrl, workReaderUrl } from "./workspacePageUrls.js";

describe("workspacePageUrls", () => {
  it("matches canonical standalone builders (parity)", () => {
    expect(workReaderUrl("w1")).toBe(buildStandaloneTracePath(READER_PATH, "w1", {}));
    expect(workGraphUrl("w1", "ws")).toBe(
      buildStandaloneTracePath(GRAPH_PATH, "w1", { workspaceId: "ws" }),
    );
    expect(workGraphUrl("", "ws-only")).toBe(
      buildStandaloneTracePath(GRAPH_PATH, "", { workspaceId: "ws-only" }),
    );
    expect(workChatUrl("w1", "ws")).toBe(buildStandaloneChatPath("w1", { workspaceId: "ws" }));
    expect(workChatUrl("", "ws-only")).toBe(buildStandaloneChatPath("", { workspaceId: "ws-only" }));
  });
});
