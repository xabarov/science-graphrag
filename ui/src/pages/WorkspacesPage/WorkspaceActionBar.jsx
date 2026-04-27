import React from "react";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import AddOutlinedIcon from "@mui/icons-material/AddOutlined";
import DownloadOutlinedIcon from "@mui/icons-material/DownloadOutlined";
import UploadFileOutlinedIcon from "@mui/icons-material/UploadFileOutlined";

import { CursorIconAction } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
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
 *   exportWorkspacesJson: () => void,
 *   onImportClick: () => void,
 * }} props
 */
export default function WorkspaceActionBar({
  workspaces,
  wsLoading,
  newWsName,
  onNewWsNameChange,
  onCreateWorkspace,
  targetWorkspaceId,
  onTargetWorkspaceChange,
  exportWorkspacesJson,
  onImportClick,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;

  function handleTargetChange(nextId) {
    onTargetWorkspaceChange(nextId);
    if (nextId) {
      setActiveWorkspaceId(nextId);
    }
  }

  return (
    <Box
      sx={{
        mb: 1.75,
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: 1,
        p: { xs: 1, sm: 1.1 },
        borderRadius: "6px",
        border: `1px solid ${tk.border.default}`,
        backgroundColor: tk.surface.sidebar,
      }}
    >
      {wsLoading ? <CircularProgress size={18} sx={{ color: tk.accent.fg, flexShrink: 0 }} /> : null}

      <Box
        component="form"
        onSubmit={(event) => {
          event.preventDefault();
          onCreateWorkspace();
        }}
        sx={{
          display: "flex",
          gap: 0.5,
          alignItems: "center",
          minWidth: { xs: "100%", sm: 200 },
          flex: { xs: "1 1 100%", sm: "1 1 220px" },
          maxWidth: { sm: 360 },
        }}
      >
        <TextField
          label={t("workspaces.newWsLabel")}
          value={newWsName}
          onChange={(event) => onNewWsNameChange(event.target.value)}
          size="small"
          fullWidth
          sx={{
            minWidth: 0,
            "& .MuiInputBase-input": { fontSize: "0.8125rem" },
            "& .MuiInputLabel-root": { fontSize: "0.8125rem" },
          }}
        />
        <CursorIconAction type="submit" title={t("workspaces.create")} aria-label={t("workspaces.create")}>
          <AddOutlinedIcon sx={{ fontSize: "1.05rem" }} />
        </CursorIconAction>
      </Box>

      {workspaces.length ? (
        <FormControl size="small" sx={{ minWidth: { xs: "100%", sm: 200 }, flex: { sm: "1 1 200px" }, maxWidth: { sm: 400 } }}>
          <InputLabel id="workspace-target-select">{t("workspaces.targetLabel")}</InputLabel>
          <Select
            labelId="workspace-target-select"
            label={t("workspaces.targetLabel")}
            value={targetWorkspaceId}
            onChange={(event) => handleTargetChange(event.target.value)}
          >
            {workspaces.map((ws) => (
              <MenuItem key={ws.id} value={ws.id}>
                {ws.name || ws.id}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      ) : (
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, flex: "1 1 auto" }}>
          {t("workspaces.targetHint")}
        </Typography>
      )}

      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, ml: { xs: 0, sm: "auto" } }}>
        <CursorIconAction type="button" title={t("workspaces.exportJson")} onClick={exportWorkspacesJson}>
          <DownloadOutlinedIcon sx={{ fontSize: "1.05rem" }} />
        </CursorIconAction>
        <CursorIconAction type="button" title={t("workspaces.importJson")} onClick={onImportClick}>
          <UploadFileOutlinedIcon sx={{ fontSize: "1.05rem" }} />
        </CursorIconAction>
      </Box>
    </Box>
  );
}
