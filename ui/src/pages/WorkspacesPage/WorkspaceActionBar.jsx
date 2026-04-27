import React from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import AddOutlinedIcon from "@mui/icons-material/AddOutlined";
import DownloadOutlinedIcon from "@mui/icons-material/DownloadOutlined";
import UploadFileOutlinedIcon from "@mui/icons-material/UploadFileOutlined";
import AutoAwesomeOutlinedIcon from "@mui/icons-material/AutoAwesomeOutlined";

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
 *   totalAttachedWorks: number,
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
  totalAttachedWorks,
  exportWorkspacesJson,
  onImportClick,
}) {
  const { t } = useI18n();
  const targetWorkspace = workspaces.find((ws) => ws.id === targetWorkspaceId) || null;

  function handleTargetChange(nextId) {
    onTargetWorkspaceChange(nextId);
    if (nextId) {
      setActiveWorkspaceId(nextId);
    }
  }

  return (
    <Box
      sx={{
        mb: 2,
        p: { xs: 1.5, sm: 1.75 },
        borderRadius: "6px",
        border: "1px solid rgba(99,102,241,0.22)",
        background:
          "linear-gradient(180deg, rgba(99,102,241,0.10) 0%, rgba(99,102,241,0.04) 100%)",
      }}
    >
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 1.25,
          mb: 1.5,
        }}
      >
        <Box sx={{ minWidth: 0, display: "flex", alignItems: "flex-start", gap: 0.9 }}>
          <Box
            sx={{
              width: 32,
              height: 32,
              borderRadius: "6px",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              border: "1px solid rgba(99,102,241,0.26)",
              backgroundColor: "rgba(99,102,241,0.12)",
              color: "rgba(129,140,248,0.95)",
              flexShrink: 0,
            }}
          >
            <AutoAwesomeOutlinedIcon sx={{ fontSize: "1rem" }} />
          </Box>
          <Box sx={{ minWidth: 0 }}>
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)", mb: 0.5 }}>
              {t("workspaces.toolbar.title")}
            </Typography>
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.64)", lineHeight: 1.5 }}>
              {t("workspaces.toolbar.desc")}
            </Typography>
          </Box>
        </Box>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 0.6,
            flexWrap: "wrap",
            flexShrink: 0,
            p: 0.4,
            borderRadius: "999px",
            border: "1px solid rgba(255,255,255,0.08)",
            backgroundColor: "rgba(10,10,10,0.18)",
          }}
        >
          {wsLoading ? <CircularProgress size={18} sx={{ color: "rgba(129,140,248,0.95)" }} /> : null}
          <CursorIconAction type="button" title={t("workspaces.exportJson")} onClick={exportWorkspacesJson}>
            <DownloadOutlinedIcon sx={{ fontSize: "1.05rem" }} />
          </CursorIconAction>
          <CursorIconAction type="button" title={t("workspaces.importJson")} onClick={onImportClick}>
            <UploadFileOutlinedIcon sx={{ fontSize: "1.05rem" }} />
          </CursorIconAction>
        </Box>
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", xl: "minmax(220px, 1fr) minmax(260px, 1fr) auto" },
          gap: 1,
          alignItems: "center",
        }}
      >
        <Box
          component="form"
          onSubmit={(event) => {
            event.preventDefault();
            onCreateWorkspace();
          }}
          sx={{
            display: "flex",
            gap: 0.75,
            alignItems: "center",
            minWidth: 0,
            p: 0.6,
            borderRadius: "6px",
            border: "1px solid rgba(255,255,255,0.08)",
            backgroundColor: "rgba(10,10,10,0.16)",
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
          <CursorIconAction
            type="submit"
            title={t("workspaces.create")}
            aria-label={t("workspaces.create")}
          >
            <AddOutlinedIcon sx={{ fontSize: "1.05rem" }} />
          </CursorIconAction>
        </Box>

        {workspaces.length ? (
          <FormControl
            size="small"
            fullWidth
            sx={{
              "& .MuiOutlinedInput-root": {
                backgroundColor: "rgba(10,10,10,0.16)",
              },
            }}
          >
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
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.48)" }}>
            {t("workspaces.targetHint")}
          </Typography>
        )}

        <Box
          sx={{
            display: "flex",
            flexWrap: "wrap",
            gap: 0.75,
            justifyContent: { xs: "flex-start", xl: "flex-end" },
            p: { xs: 0, xl: 0.6 },
            borderRadius: { xs: 0, xl: "6px" },
            border: { xs: "none", xl: "1px solid rgba(255,255,255,0.08)" },
            backgroundColor: { xs: "transparent", xl: "rgba(10,10,10,0.14)" },
          }}
        >
          <Chip label={t("workspaces.stats.workspaces", { count: workspaces.length })} size="small" sx={{ height: 24, fontSize: "0.6875rem", backgroundColor: "rgba(255,255,255,0.08)" }} />
          <Chip label={t("workspaces.stats.papers", { count: totalAttachedWorks })} size="small" sx={{ height: 24, fontSize: "0.6875rem", backgroundColor: "rgba(255,255,255,0.08)" }} />
          <Chip
            label={targetWorkspace ? t("workspaces.stats.target", { name: targetWorkspace.name || targetWorkspace.id }) : t("workspaces.stats.targetNone")}
            size="small"
            sx={{
              height: 24,
              fontSize: "0.6875rem",
              maxWidth: "100%",
              backgroundColor: targetWorkspace ? "rgba(99,102,241,0.15)" : "rgba(255,255,255,0.08)",
              color: targetWorkspace ? "rgba(129,140,248,0.95)" : "rgba(255,255,255,0.68)",
              "& .MuiChip-label": { display: "block", overflow: "hidden", textOverflow: "ellipsis" },
            }}
          />
        </Box>
      </Box>
    </Box>
  );
}
