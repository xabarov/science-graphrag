import { formatWorkPrimaryLabel } from "../answer/workListLabel.js";

/**
 * @param {{
 *   workId: string,
 *   resolvedWork: Record<string, unknown> | null,
 *   corpusWorkspaceOnly: boolean,
 *   standaloneMode: boolean,
 *   workspaceId: string,
 * }} args
 * @param {(key: string, vars?: Record<string, string>) => string} t
 */
export function deriveChatContextSummaryLabel(
  { workId, resolvedWork, corpusWorkspaceOnly, standaloneMode, workspaceId },
  t,
) {
  const w = String(workId || "").trim();
  if (w) {
    const rw = resolvedWork && String(resolvedWork.work_id ?? "").trim() === w ? resolvedWork : null;
    return formatWorkPrimaryLabel(rw || { work_id: w }, w);
  }
  if (corpusWorkspaceOnly && String(workspaceId || "").trim()) {
    return t("chat.context.wholeWorkspace");
  }
  if (standaloneMode) {
    return t("chat.context.globalCorpus");
  }
  return t("chat.context.notSet");
}
