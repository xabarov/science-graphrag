import React from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import CircularProgress from "@mui/material/CircularProgress";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";

import { CursorPrimaryButton, CursorSmallButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { buildWorkspacePath } from "../WorkspacePage/utils/workContext.js";
import { setActiveWorkspaceId } from "../../utils/workspaceStore.js";

/**
 * @param {{
 *   workspaces: Array<{ id: string, name?: string, work_ids?: string[] }>,
 *   wsLoading: boolean,
 *   newWsName: string,
 *   onNewWsNameChange: (v: string) => void,
 *   onCreateWorkspace: () => void,
 *   targetWorkspaceId: string,
 *   onTargetWorkspaceChange: (id: string) => void,
 *   onRenameWorkspace: (id: string, name: string) => void,
 *   onDeleteWorkspace: (id: string) => void,
 *   mergeKeep: string,
 *   mergeDrop: string,
 *   mergeBusy: boolean,
 *   onMergeKeepChange: (v: string) => void,
 *   onMergeDropChange: (v: string) => void,
 *   onMergeWorkspaces: () => void,
 *   exportWorkspacesJson: () => void,
 *   onImportWorkspaces: (ev: React.ChangeEvent<HTMLInputElement>) => void,
 * }} props
 */
export default function WorkspaceCollectionPanel({
  workspaces,
  wsLoading,
  newWsName,
  onNewWsNameChange,
  onCreateWorkspace,
  targetWorkspaceId,
  onTargetWorkspaceChange,
  onRenameWorkspace,
  onDeleteWorkspace,
  mergeKeep,
  mergeDrop,
  mergeBusy,
  onMergeKeepChange,
  onMergeDropChange,
  onMergeWorkspaces,
  exportWorkspacesJson,
  onImportWorkspaces,
}) {
  const { t } = useI18n();

  return (
    <Box sx={{ p: 1.75, borderRadius: "6px", border: "1px solid rgba(99,102,241,0.24)", backgroundColor: "rgba(99,102,241,0.08)" }}>
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)", mb: 0.75 }}>{t("workspaces.wsPanel.title")}</Typography>
      {wsLoading ? (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <CircularProgress size={20} />
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)" }}>{t("workspaces.loading")}</Typography>
        </Box>
      ) : workspaces.length === 0 ? (
        <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.62)" }}>{t("workspaces.emptyWs")}</Typography>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
          {workspaces.map((ws) => (
            <Box
              key={ws.id}
              sx={{
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 1,
                borderBottom: "1px solid rgba(255,255,255,0.06)",
                pb: 0.75,
              }}
            >
              <Box sx={{ minWidth: 0 }}>
                <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>{ws.name || ws.id}</Typography>
                <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.42)", fontFamily: "monospace" }}>{ws.id}</Typography>
                <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.45)" }}>
                  {t("workspaces.papersCount", { count: (ws.work_ids || []).length })}
                </Typography>
              </Box>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                <CursorSmallButton
                  component={Link}
                  to={buildWorkspacePath("", "overview", { workspaceId: ws.id })}
                  onClick={() => setActiveWorkspaceId(ws.id)}
                  sx={{ textDecoration: "none" }}
                >
                  {t("workspaces.open")}
                </CursorSmallButton>
                <CursorSmallButton
                  type="button"
                  onClick={() => {
                    const n = window.prompt(t("workspaces.renamePromptTitle"), ws.name || "");
                    if (n != null && String(n).trim()) onRenameWorkspace(ws.id, String(n).trim());
                  }}
                >
                  {t("workspaces.rename")}
                </CursorSmallButton>
                <CursorSmallButton type="button" onClick={() => onDeleteWorkspace(ws.id)}>
                  {t("workspaces.delete")}
                </CursorSmallButton>
              </Box>
            </Box>
          ))}
        </Box>
      )}
      <Box sx={{ mt: 1.5, display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
        <TextField
          label={t("workspaces.newWsLabel")}
          value={newWsName}
          onChange={(e) => onNewWsNameChange(e.target.value)}
          size="small"
          sx={{ minWidth: 180, "& .MuiInputBase-input": { fontSize: "0.8125rem" } }}
        />
        <CursorPrimaryButton type="button" onClick={() => onCreateWorkspace()}>
          {t("workspaces.create")}
        </CursorPrimaryButton>
      </Box>
      <Box sx={{ mt: 1.5 }}>
        {workspaces.length ? (
          <FormControl size="small" sx={{ minWidth: 220 }}>
            <InputLabel id="target-ws">{t("workspaces.targetLabel")}</InputLabel>
            <Select
              labelId="target-ws"
              label={t("workspaces.targetLabel")}
              value={targetWorkspaceId}
              onChange={(e) => {
                onTargetWorkspaceChange(e.target.value);
                setActiveWorkspaceId(e.target.value);
              }}
            >
              {workspaces.map((ws) => (
                <MenuItem key={ws.id} value={ws.id}>
                  {ws.name || ws.id}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        ) : (
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}>{t("workspaces.targetHint")}</Typography>
        )}
      </Box>
      <Box sx={{ mt: 1.5, display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
        <CursorSmallButton type="button" onClick={exportWorkspacesJson}>
          {t("workspaces.exportJson")}
        </CursorSmallButton>
        <CursorSmallButton component="label" sx={{ cursor: "pointer" }}>
          {t("workspaces.importJson")}
          <input type="file" accept="application/json" hidden onChange={onImportWorkspaces} />
        </CursorSmallButton>
      </Box>
      <Box sx={{ mt: 1.5, display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
        <TextField
          label={t("workspaces.mergeKeep")}
          value={mergeKeep}
          onChange={(e) => onMergeKeepChange(e.target.value)}
          size="small"
          sx={{ minWidth: 200, "& .MuiInputBase-input": { fontSize: "0.75rem" } }}
        />
        <TextField
          label={t("workspaces.mergeDrop")}
          value={mergeDrop}
          onChange={(e) => onMergeDropChange(e.target.value)}
          size="small"
          sx={{ minWidth: 200, "& .MuiInputBase-input": { fontSize: "0.75rem" } }}
        />
        <CursorPrimaryButton type="button" disabled={mergeBusy} onClick={() => onMergeWorkspaces()}>
          {t("workspaces.merge")}
        </CursorPrimaryButton>
      </Box>
    </Box>
  );
}
