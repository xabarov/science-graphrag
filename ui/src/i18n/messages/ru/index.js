import { mergeMessages } from "../../mergeMessages.js";
import partAskPanel from "./partAskPanel.js";
import partBenchmarkCaseDialog from "./partBenchmarkCaseDialog.js";
import partBenchmarkPage from "./partBenchmarkPage.js";
import partBenchmarkTabs from "./partBenchmarkTabs.js";
import partChat from "./partChat.js";
import partCommon from "./partCommon.js";
import partEvidenceBody from "./partEvidenceBody.js";
import partGraphUi from "./partGraphUi.js";
import partPagesCore from "./partPagesCore.js";
import partReaderBody from "./partReaderBody.js";
import partReaderShell from "./partReaderShell.js";
import partSession from "./partSession.js";
import partSettings from "./partSettings.js";
import partShell from "./partShell.js";
import partWorkspacePage from "./partWorkspacePage.js";
import partWorkspaces from "./partWorkspaces.js";
import partWorkspaceTabs from "./partWorkspaceTabs.js";

/** @type {Record<string, string>} */
export default mergeMessages(
  partShell,
  partPagesCore,
  partCommon,
  partWorkspaces,
  partWorkspacePage,
  partWorkspaceTabs,
  partSettings,
  partSession,
  partChat,
  partAskPanel,
  partGraphUi,
  partReaderBody,
  partReaderShell,
  partEvidenceBody,
  partBenchmarkPage,
  partBenchmarkCaseDialog,
  partBenchmarkTabs,
);
