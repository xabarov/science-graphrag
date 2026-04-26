import { createContext } from "react";

/**
 * @typedef {{ id: string, name?: string, work_ids?: string[] } | null} WorkspaceMeta
 */

/**
 * @typedef {{
 *   activeWorkspaceId: string | null,
 *   activeWorkspaceMeta: WorkspaceMeta,
 *   setActiveWorkspace: (id: string) => void,
 *   getLastWorkspaceHref: () => string,
 * }} WorkspaceContextValue
 */

/** @type {import("react").Context<WorkspaceContextValue | null>} */
export const WorkspaceContext = createContext(null);
