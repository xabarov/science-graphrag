import React, { useState } from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Alert from "@mui/material/Alert";
import Typography from "@mui/material/Typography";

import { CursorPrimaryButton, CursorSmallButton } from "../../components/common/index.js";
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
    <Box
      sx={{
        p: { xs: 1.5, sm: 2 },
        ...mainShellContentSx,
        flex: 1,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <WorkspaceHero t={t} vm={vm} />

      {vm.workspaceError && vm.workspaceMeta.id ? (
        <Alert severity="error" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {vm.workspaceError}
        </Alert>
      ) : null}

      {!vm.workspaceLoading && !vm.workspaceMeta.id && !vm.workspaceError ? (
        vm.emptyState
      ) : !vm.workspaceLoading && !vm.workspaceMeta.id && vm.workspaceError ? (
        <Box
          sx={{
            flex: 1,
            minHeight: "36vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            px: 1,
          }}
        >
          <Box
            sx={{
              maxWidth: 560,
              width: "100%",
              p: 2.5,
              borderRadius: "6px",
              border: "1px solid rgba(255,255,255,0.1)",
              backgroundColor: "#141414",
            }}
          >
            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.88)", mb: 1.5 }}>
              {vm.t("workspace.err.loadTitle")}
            </Typography>
            <Alert severity="error" sx={{ mb: 2, fontSize: "0.8125rem" }}>
              {vm.workspaceError}
            </Alert>
            {vm.workspaceErrorIsServer ? (
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 2, lineHeight: 1.55 }}>
                {vm.t("workspace.err.serverHint")}
              </Typography>
            ) : null}
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
              <CursorPrimaryButton type="button" onClick={vm.retryWorkspaceLoad}>
                {vm.t("workspace.err.retry")}
              </CursorPrimaryButton>
              <CursorSmallButton component={Link} to="/workspaces" sx={{ textDecoration: "none" }}>
                {vm.t("workspace.empty.workspaces")}
              </CursorSmallButton>
              <CursorSmallButton component={Link} to="/home" sx={{ textDecoration: "none" }}>
                {vm.t("workspace.empty.about")}
              </CursorSmallButton>
            </Box>
          </Box>
        </Box>
      ) : (
        <Box sx={{ flex: 1, minHeight: 0, minWidth: 0 }}>
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
        </Box>
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
