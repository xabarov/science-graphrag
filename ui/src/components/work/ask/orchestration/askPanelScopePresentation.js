/**
 * Banner / scope eyebrow copy for Ask panel shell.
 * @param {(key: string) => string} t
 * @param {{ inWorkspace: boolean, locked: boolean, corpusWorkspaceOnly: boolean }} flags
 */
export function deriveAskPanelScopeEyebrow(t, { inWorkspace, locked, corpusWorkspaceOnly }) {
  if (inWorkspace || locked) return t("askPanel.banner.workspaceScoped");
  if (corpusWorkspaceOnly) return t("askPanel.banner.workspaceCorpusTitle");
  return t("askPanel.banner.standalone");
}
