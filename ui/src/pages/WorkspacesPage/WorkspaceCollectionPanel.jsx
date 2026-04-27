import React from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import LayersOutlinedIcon from "@mui/icons-material/LayersOutlined";
import FolderOpenOutlinedIcon from "@mui/icons-material/FolderOpenOutlined";
import DriveFileRenameOutlineOutlinedIcon from "@mui/icons-material/DriveFileRenameOutlineOutlined";
import DeleteOutlineOutlinedIcon from "@mui/icons-material/DeleteOutlineOutlined";

import { CursorIconAction } from "../../components/common/index.js";
import { useFeedback } from "../../components/feedback/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { buildWorkspacePath } from "../WorkspacePage/utils/workContext.js";
import { setActiveWorkspaceId } from "../../utils/workspaceStore.js";

/**
 * @param {{
 *   workspaces: Array<{ id: string, name?: string, work_ids?: string[] }>,
 *   wsLoading: boolean,
 *   targetWorkspaceId: string,
 *   onTargetWorkspaceChange: (id: string) => void,
 *   onRenameWorkspace: (id: string, name: string) => void,
 *   onDeleteWorkspace: (id: string) => void,
 * }} props
 */
export default function WorkspaceCollectionPanel({
  workspaces,
  wsLoading,
  targetWorkspaceId,
  onTargetWorkspaceChange,
  onRenameWorkspace,
  onDeleteWorkspace,
}) {
  const { t } = useI18n();
  const { prompt } = useFeedback();

  function handleSelectWorkspace(workspaceId) {
    onTargetWorkspaceChange(workspaceId);
    setActiveWorkspaceId(workspaceId);
  }

  function stopCardClick(event) {
    event.stopPropagation();
  }

  return (
    <Box sx={{ p: 1.75, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#141414" }}>
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 1, mb: 1.25 }}>
        <Box sx={{ minWidth: 0 }}>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)", mb: 0.45 }}>{t("workspaces.wsPanel.title")}</Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)", lineHeight: 1.5 }}>
            {t("workspaces.wsPanel.desc")}
          </Typography>
        </Box>
        <Chip label={t("workspaces.wsPanel.total", { count: workspaces.length })} size="small" sx={{ height: 24, fontSize: "0.6875rem" }} />
      </Box>
      {wsLoading ? (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <CircularProgress size={20} />
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)" }}>{t("workspaces.loading")}</Typography>
        </Box>
      ) : workspaces.length === 0 ? (
        <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.62)" }}>{t("workspaces.emptyWs")}</Typography>
      ) : (
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", xl: "repeat(2, minmax(0, 1fr))" }, gap: 1 }}>
          {workspaces.map((ws) => (
            <Box
              key={ws.id}
              role="button"
              tabIndex={0}
              onClick={() => handleSelectWorkspace(ws.id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  handleSelectWorkspace(ws.id);
                }
              }}
              sx={{
                p: 1.4,
                borderRadius: "6px",
                border:
                  ws.id === targetWorkspaceId ? "1px solid rgba(99,102,241,0.35)" : "1px solid rgba(255,255,255,0.08)",
                backgroundColor: ws.id === targetWorkspaceId ? "rgba(99,102,241,0.08)" : "#1a1a1a",
                cursor: "pointer",
                transition: "border-color 0.15s ease, background-color 0.15s ease, transform 0.15s ease",
                "&:hover": {
                  borderColor: "rgba(255,255,255,0.16)",
                  backgroundColor: ws.id === targetWorkspaceId ? "rgba(99,102,241,0.12)" : "rgba(255,255,255,0.03)",
                  transform: "translateY(-1px)",
                },
                "&:focus-visible": {
                  outline: "1px solid rgba(99,102,241,0.55)",
                  outlineOffset: 2,
                },
              }}
            >
              <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 1 }}>
                <Box sx={{ minWidth: 0, display: "flex", alignItems: "flex-start", gap: 0.8 }}>
                  <Box
                    sx={{
                      width: 30,
                      height: 30,
                      borderRadius: "6px",
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      border: ws.id === targetWorkspaceId ? "1px solid rgba(99,102,241,0.26)" : "1px solid rgba(255,255,255,0.08)",
                      backgroundColor: ws.id === targetWorkspaceId ? "rgba(99,102,241,0.14)" : "rgba(255,255,255,0.03)",
                      color: ws.id === targetWorkspaceId ? "rgba(129,140,248,0.95)" : "rgba(255,255,255,0.62)",
                      flexShrink: 0,
                    }}
                  >
                    <LayersOutlinedIcon sx={{ fontSize: "1rem" }} />
                  </Box>
                  <Box sx={{ minWidth: 0 }}>
                    <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: "rgba(255,255,255,0.92)" }} noWrap>
                      {ws.name || ws.id}
                    </Typography>
                    <Typography
                      sx={{
                        fontSize: "0.7rem",
                        color: "rgba(255,255,255,0.42)",
                        fontFamily: "monospace",
                        mt: 0.35,
                      }}
                      noWrap
                    >
                      {ws.id}
                    </Typography>
                  </Box>
                </Box>
                <Box sx={{ display: "flex", gap: 0.45, flexShrink: 0 }}>
                  <CursorIconAction
                    component={Link}
                    to={buildWorkspacePath("", "overview", { workspaceId: ws.id })}
                    onClick={(event) => {
                      stopCardClick(event);
                      setActiveWorkspaceId(ws.id);
                    }}
                    title={t("workspaces.open")}
                  >
                    <FolderOpenOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                  </CursorIconAction>
                  <CursorIconAction
                    type="button"
                    onClick={async (event) => {
                      stopCardClick(event);
                      const nextName = await prompt({
                        title: t("workspaces.renamePromptTitle"),
                        label: t("workspaces.renameDialogLabel"),
                        defaultValue: ws.name || "",
                        confirmLabel: t("workspaces.renameDialogSave"),
                        cancelLabel: t("chat.clear.cancel"),
                        validate: (v) => (!String(v).trim() ? t("workspaces.renameDialogErrorEmpty") : null),
                      });
                      if (nextName != null) {
                        onRenameWorkspace(ws.id, nextName);
                      }
                    }}
                    title={t("workspaces.rename")}
                  >
                    <DriveFileRenameOutlineOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                  </CursorIconAction>
                  <CursorIconAction
                    type="button"
                    onClick={(event) => {
                      stopCardClick(event);
                      onDeleteWorkspace(ws.id);
                    }}
                    title={t("workspaces.delete")}
                    sx={{
                      color: "rgba(239,68,68,0.72)",
                      borderColor: "rgba(239,68,68,0.16)",
                      "&:hover": {
                        background: "rgba(239,68,68,0.08)",
                        color: "rgba(255,255,255,0.92)",
                      },
                    }}
                  >
                    <DeleteOutlineOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                  </CursorIconAction>
                </Box>
              </Box>
              <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
                <Chip label={t("workspaces.papersCount", { count: (ws.work_ids || []).length })} size="small" sx={{ height: 22, fontSize: "0.6875rem" }} />
                {ws.id === targetWorkspaceId ? (
                  <Chip
                    label={t("workspaces.targetSelected")}
                    size="small"
                    sx={{
                      height: 22,
                      fontSize: "0.6875rem",
                      backgroundColor: "rgba(99,102,241,0.18)",
                      color: "rgba(129,140,248,0.95)",
                      border: "1px solid rgba(99,102,241,0.28)",
                    }}
                  />
                ) : (
                  <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.38)" }}>
                    {t("workspaces.wsPanel.clickToTarget")}
                  </Typography>
                )}
              </Box>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}
