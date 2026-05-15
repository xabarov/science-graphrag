/**
 * Client helpers for workspace API + active workspace pointer in localStorage.
 *
 * Implementation is split under `utils/workspaceStore/` (read / write / ingest / routing);
 * this module re-exports the public surface for stable import paths.
 */

export { getActiveWorkspaceId, setActiveWorkspaceId } from "./activeWorkspacePointer.js";

export * from "./workspaceStore/workspaceRead.js";
export * from "./workspaceStore/workspaceWrite.js";
export * from "./workspaceStore/workspaceIngest.js";
export * from "./workspaceStore/workspaceRouting.js";
