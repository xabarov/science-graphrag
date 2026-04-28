import { describe, expect, it } from "vitest";

import { GRAPH_PAGE_QUERY_KEYS, preserveGraphPageOptionalParams, readGraphPageLayoutFlags } from "./graphPageQuery.js";
import { WORKSPACE_SHELL_QUERY_KEYS } from "./queryKeys.js";

describe("graphPageQuery", () => {
  it("readGraphPageLayoutFlags parses compact and focus", () => {
    expect(readGraphPageLayoutFlags(new URLSearchParams())).toEqual({
      compact: false,
      focus: false,
      compactLayout: false,
    });
    expect(readGraphPageLayoutFlags(new URLSearchParams(`${GRAPH_PAGE_QUERY_KEYS.compact}=1`))).toEqual({
      compact: true,
      focus: false,
      compactLayout: true,
    });
    expect(readGraphPageLayoutFlags(new URLSearchParams(`${GRAPH_PAGE_QUERY_KEYS.focus}=1`))).toEqual({
      compact: false,
      focus: true,
      compactLayout: true,
    });
    expect(
      readGraphPageLayoutFlags(
        new URLSearchParams(`${GRAPH_PAGE_QUERY_KEYS.compact}=1&${GRAPH_PAGE_QUERY_KEYS.focus}=1`),
      ),
    ).toEqual({
      compact: true,
      focus: true,
      compactLayout: true,
    });
  });

  it("preserveGraphPageOptionalParams copies lab, compact, focus", () => {
    const prev = new URLSearchParams(
      `${GRAPH_PAGE_QUERY_KEYS.lab}=1&${GRAPH_PAGE_QUERY_KEYS.compact}=1&${GRAPH_PAGE_QUERY_KEYS.focus}=1&${WORKSPACE_SHELL_QUERY_KEYS.workId}=w1`,
    );
    const params = new URLSearchParams();
    params.set(WORKSPACE_SHELL_QUERY_KEYS.workId, "w2");
    preserveGraphPageOptionalParams(params, prev);
    expect(params.get(WORKSPACE_SHELL_QUERY_KEYS.workId)).toBe("w2");
    expect(params.get(GRAPH_PAGE_QUERY_KEYS.lab)).toBe("1");
    expect(params.get(GRAPH_PAGE_QUERY_KEYS.compact)).toBe("1");
    expect(params.get(GRAPH_PAGE_QUERY_KEYS.focus)).toBe("1");
  });

  it("preserveGraphPageOptionalParams skips absent flags", () => {
    const prev = new URLSearchParams(`${WORKSPACE_SHELL_QUERY_KEYS.workId}=w1`);
    const params = new URLSearchParams();
    preserveGraphPageOptionalParams(params, prev);
    expect([...params.keys()].sort()).toEqual([]);
  });

  it("preserveGraphPageOptionalParams copies workspace_id when present", () => {
    const prev = new URLSearchParams(
      `${WORKSPACE_SHELL_QUERY_KEYS.workId}=w1&${WORKSPACE_SHELL_QUERY_KEYS.workspaceId}=ws-9`,
    );
    const params = new URLSearchParams();
    params.set(WORKSPACE_SHELL_QUERY_KEYS.workId, "w2");
    preserveGraphPageOptionalParams(params, prev);
    expect(params.get(WORKSPACE_SHELL_QUERY_KEYS.workId)).toBe("w2");
    expect(params.get(WORKSPACE_SHELL_QUERY_KEYS.workspaceId)).toBe("ws-9");
  });
});
