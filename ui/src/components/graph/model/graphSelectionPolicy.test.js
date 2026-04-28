import { describe, expect, it } from "vitest";

import { reconcileGraphWorkspaceSelection } from "./graphSelectionPolicy.js";

describe("reconcileGraphWorkspaceSelection", () => {
  it("canonicalizes node id when resolved differs from selected", () => {
    expect(
      reconcileGraphWorkspaceSelection({
        selectedNodeId: "wrong",
        selectedEdgeId: "",
        resolvedSelectedNodeId: "ok",
        resolvedSelectedEdgeId: "",
      }),
    ).toEqual({ nodeId: "ok", edgeId: "", changed: true });
  });

  it("clears orphan edge when edge not resolved", () => {
    expect(
      reconcileGraphWorkspaceSelection({
        selectedNodeId: "",
        selectedEdgeId: "missing",
        resolvedSelectedNodeId: "",
        resolvedSelectedEdgeId: "",
      }),
    ).toEqual({ nodeId: "", edgeId: "", changed: true });
  });

  it("clears node when edge is resolved and node was selected", () => {
    expect(
      reconcileGraphWorkspaceSelection({
        selectedNodeId: "n1",
        selectedEdgeId: "e1",
        resolvedSelectedNodeId: "",
        resolvedSelectedEdgeId: "e1",
      }),
    ).toEqual({ nodeId: "", edgeId: "e1", changed: true });
  });

  it("clears edge when node is resolved and edge was selected", () => {
    expect(
      reconcileGraphWorkspaceSelection({
        selectedNodeId: "n1",
        selectedEdgeId: "e1",
        resolvedSelectedNodeId: "n1",
        resolvedSelectedEdgeId: "",
      }),
    ).toEqual({ nodeId: "n1", edgeId: "", changed: true });
  });

  it("returns changed false when already consistent", () => {
    expect(
      reconcileGraphWorkspaceSelection({
        selectedNodeId: "n1",
        selectedEdgeId: "",
        resolvedSelectedNodeId: "n1",
        resolvedSelectedEdgeId: "",
      }),
    ).toEqual({ nodeId: "n1", edgeId: "", changed: false });
  });
});
