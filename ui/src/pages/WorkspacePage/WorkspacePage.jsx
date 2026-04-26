import React from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Alert from "@mui/material/Alert";
import Typography from "@mui/material/Typography";

import FolderOpenOutlinedIcon from "@mui/icons-material/FolderOpenOutlined";
import HomeOutlinedIcon from "@mui/icons-material/HomeOutlined";
import RefreshOutlinedIcon from "@mui/icons-material/RefreshOutlined";

import { CursorIconAction } from "../../components/common/index.js";
import IngestConflictReviewCard from "../../components/dedup/IngestConflictReviewCard.jsx";
import WorkspaceDialogs from "./WorkspaceDialogs.jsx";
import WorkspaceHero from "./WorkspaceHero.jsx";
import WorkspaceLayout from "./WorkspaceLayout.jsx";
import WorkspacePaperList from "./WorkspacePaperList.jsx";
import WorkspaceSidePanel from "./WorkspaceSidePanel.jsx";
import { useWorkspacePageCore } from "./useWorkspacePageCore.jsx";

export default function WorkspacePage() {
  const vm = useWorkspacePageCore();
  const { t } = vm;

  return (
    <Box
      sx={{
        p: { xs: 1.5, sm: 2 },
        width: "100%",
        maxWidth: "none",
        boxSizing: "border-box",
        flex: 1,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
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
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
              <CursorIconAction type="button" title={vm.t("workspace.err.retry")} onClick={vm.retryWorkspaceLoad}>
                <RefreshOutlinedIcon sx={{ fontSize: "1.1rem" }} />
              </CursorIconAction>
              <CursorIconAction component={Link} to="/workspaces" title={vm.t("workspace.empty.workspaces")}>
                <FolderOpenOutlinedIcon sx={{ fontSize: "1.1rem" }} />
              </CursorIconAction>
              <CursorIconAction component={Link} to="/home" title={vm.t("workspace.empty.about")}>
                <HomeOutlinedIcon sx={{ fontSize: "1.1rem" }} />
              </CursorIconAction>
            </Box>
          </Box>
        </Box>
      ) : (
        <Box sx={{ flex: 1, minHeight: 0, minWidth: 0, overflow: "auto" }}>
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

                {vm.ingestDedupPanelOpen ? (
                  <IngestConflictReviewCard
                    workspaceId={vm.workspaceMeta.id}
                    onDismiss={vm.dismissIngestDedupPanel}
                    onMerged={vm.refreshWorkspaceMeta}
                  />
                ) : null}
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
