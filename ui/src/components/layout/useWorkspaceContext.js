import { useContext } from "react";

import { WorkspaceContext } from "./WorkspaceContextInstance.js";

/** @returns {import("./WorkspaceContextInstance.js").WorkspaceContextValue} */
export function useWorkspaceContext() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) {
    throw new Error("useWorkspaceContext must be used within WorkspaceContextProvider");
  }
  return ctx;
}
