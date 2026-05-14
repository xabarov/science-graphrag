/**
 * Canonical list of keys returned by `useAskPanelOrchestration`.
 *
 * Primary consumer: [`AskPanel.jsx`](./AskPanel.jsx) (`o.<key>`).
 * Keep this list in sync with the hook's `return { ... }` object whenever the public surface changes.
 *
 * @type {readonly string[]}
 */
export const ASK_PANEL_ORCHESTRATION_RETURN_KEYS = Object.freeze(
  [
    "t",
    "locked",
    "scopedWorkId",
    "workspaceId",
    "scopeKey",
    "workspaceWorkId",
    "query",
    "setQuery",
    "workId",
    "workDetailsForChip",
    "workspaceSearchOptions",
    "error",
    "normalized",
    "history",
    "retrievalJsonOpen",
    "setRetrievalJsonOpen",
    "sessionList",
    "activeSessionId",
    "agentToolTrace",
    "streamEvents",
    "pendingUserQuery",
    "streamingTarget",
    "inWorkspace",
    "corpusWorkspaceOnly",
    "standaloneMode",
    "starterPromptKeys",
    "isLoading",
    "abort",
    "onSubmit",
    "onActiveSessionChange",
    "onNewSession",
    "onRestartFromTurn",
    "onClearChat",
    "onDeleteSession",
    "onDeleteTurn",
    "onCopyUserText",
    "onCopyAssistantEntry",
    "searchWorks",
    "onArticlePicked",
    "handleWorkIdChange",
    "standaloneChatPath",
    "scopeEyebrow",
    "streamingHint",
    "researchPlanForPanel",
    "researchPlanStreamHint",
    "openStructuredQuestion",
    "onStructuredAnswersSubmit",
  ].sort((a, b) => a.localeCompare(b)),
);
