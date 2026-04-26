import React, { useState } from "react";
import Box from "@mui/material/Box";
import Alert from "@mui/material/Alert";

import { mainShellContentSx } from "../../components/layout/mainShellContentSx.js";
import WorkspaceDedupSection from "./WorkspaceDedupSection.jsx";
import WorkspaceDialogs from "./WorkspaceDialogs.jsx";
import WorkspaceHero from "./WorkspaceHero.jsx";
import WorkspaceLayout from "./WorkspaceLayout.jsx";
import WorkspacePaperList from "./WorkspacePaperList.jsx";
import WorkspaceSidePanel from "./WorkspaceSidePanel.jsx";
import { useWorkspacePageCore } from "./useWorkspacePageCore.jsx";

export default function WorkspacePage() {
  const vm = useWorkspacePageCore();
  const { t } = vm;
  const [sideDedupRefresh, setSideDedupRefresh] = useState(0);

  return (
    <Box sx={{ p: { xs: 1.5, sm: 2 }, ...mainShellContentSx }}>
      <WorkspaceHero t={t} vm={vm} />

      {vm.workspaceError ? (
        <Alert severity="error" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {vm.workspaceError}
        </Alert>
      ) : null}

      {!vm.workspaceLoading && !vm.workspaceMeta.id ? (
        vm.emptyState
      ) : (
        <WorkspaceLayout
          main={
            <Box>
              <WorkspacePaperList
                workspaceId={vm.workspaceMeta.id}
                effectiveWorkIds={vm.effectiveWorkIds}
                papers={vm.papers}
                selectedWorkId={vm.selectedWorkId}
                onCardActivate={vm.onCardActivate}
              />

              <WorkspaceDedupSection
                workspaceId={vm.workspaceMeta.id}
                onMerged={() => {
                  void vm.refreshWorkspaceMeta();
                  setSideDedupRefresh((n) => n + 1);
                }}
              />
            </Box>
          }
          side={
            <WorkspaceSidePanel
              workspaceId={vm.workspaceMeta.id}
              graphStats={vm.graphStats}
              uploadBusy={vm.uploadBusy}
              ingestJobId={vm.ingestJobId}
              ingestJob={vm.ingestJob}
              ingestErr={vm.ingestErr}
              onUploadDocument={vm.handleUploadDocument}
              onUploadBatch={vm.handleUploadBatch}
              addWorkInput={vm.addWorkInput}
              onAddWorkInputChange={vm.setAddWorkInput}
              addBusy={vm.addBusy}
              onAddWork={vm.handleAddWork}
              addErr={vm.addErr}
              sideDedupRefresh={sideDedupRefresh}
            />
          }
        />
      )}

      <WorkspaceDialogs
        t={t}
        summaryOpen={vm.summaryOpen}
        onSummaryClose={() => vm.setSummaryOpen(false)}
        summaryText={vm.summaryText}
        ideaOpen={vm.ideaOpen}
        onIdeaClose={() => vm.setIdeaOpen(false)}
        ideaResult={vm.ideaResult}
        ideaBusy={vm.ideaBusy}
        ideaError={vm.ideaError}
      />
    </Box>
  );
}
