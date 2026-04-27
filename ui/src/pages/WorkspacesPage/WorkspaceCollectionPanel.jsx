import React, { useState } from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import CircularProgress from "@mui/material/CircularProgress";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import LayersOutlinedIcon from "@mui/icons-material/LayersOutlined";
import FolderOpenOutlinedIcon from "@mui/icons-material/FolderOpenOutlined";
import MoreVertOutlinedIcon from "@mui/icons-material/MoreVertOutlined";

import { CursorIconAction } from "../../components/common/index.js";
import { useFeedback } from "../../components/feedback/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { buildWorkspacePath } from "../WorkspacePage/utils/workContext.js";
import { setActiveWorkspaceId } from "../../utils/workspaceStore.js";

function shortWorkspaceId(id) {
  const s = String(id || "");
  if (s.length <= 14) return s;
  return `${s.slice(0, 6)}…${s.slice(-4)}`;
}

/**
 * @param {{
 *   workspaces: Array<{ id: string, name?: string, work_ids?: string[] }>,
 *   wsLoading: boolean,
 *   targetWorkspaceId: string,
 *   onRenameWorkspace: (id: string, name: string) => void,
 *   onDeleteWorkspace: (id: string) => void,
 * }} props
 */
export default function WorkspaceCollectionPanel({
  workspaces,
  wsLoading,
  targetWorkspaceId,
  onRenameWorkspace,
  onDeleteWorkspace,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const { prompt } = useFeedback();
  const [menuAnchor, setMenuAnchor] = useState(null);
  const [menuWorkspaceId, setMenuWorkspaceId] = useState(null);

  function openMenu(event, workspaceId) {
    setMenuAnchor(event.currentTarget);
    setMenuWorkspaceId(workspaceId);
  }

  function closeMenu() {
    setMenuAnchor(null);
    setMenuWorkspaceId(null);
  }

  const menuWorkspace = workspaces.find((w) => w.id === menuWorkspaceId) || null;

  return (
    <Box sx={{ p: 1.5, borderRadius: "6px", border: `1px solid ${tk.border.default}`, backgroundColor: tk.surface.sidebar }}>
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 1, mb: 1 }}>
        <Typography sx={{ fontSize: "0.8125rem", fontWeight: 600, color: tk.text.primary }}>{t("workspaces.wsPanel.title")}</Typography>
        <Chip
          label={t("workspaces.wsPanel.total", { count: workspaces.length })}
          size="small"
          sx={{ height: 22, fontSize: "0.6875rem", border: `1px solid ${tk.border.default}`, color: tk.text.secondary, backgroundColor: tk.surface.panel }}
        />
      </Box>
      {wsLoading ? (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <CircularProgress size={20} />
          <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted }}>{t("workspaces.loading")}</Typography>
        </Box>
      ) : workspaces.length === 0 ? (
        <Typography sx={{ fontSize: "0.8125rem", color: tk.text.secondary }}>{t("workspaces.emptyWs")}</Typography>
      ) : (
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", xl: "repeat(2, minmax(0, 1fr))" }, gap: 1 }}>
          {workspaces.map((ws) => (
            <Box
              key={ws.id}
              sx={{
                p: 1.25,
                borderRadius: "6px",
                border:
                  ws.id === targetWorkspaceId ? `1px solid ${tk.accent.softBorder}` : `1px solid ${tk.border.default}`,
                backgroundColor: ws.id === targetWorkspaceId ? tk.accent.softBg : tk.surface.panel,
                transition: "border-color 0.15s ease, background-color 0.15s ease",
              }}
            >
              <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 1 }}>
                <Box sx={{ minWidth: 0, display: "flex", alignItems: "flex-start", gap: 0.75 }}>
                  <Box
                    sx={{
                      width: 28,
                      height: 28,
                      borderRadius: "6px",
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      border: ws.id === targetWorkspaceId ? `1px solid ${tk.accent.softBorder}` : `1px solid ${tk.border.default}`,
                      backgroundColor: ws.id === targetWorkspaceId ? tk.accent.emphasisHoverBg : tk.control.outlinedBg,
                      color: ws.id === targetWorkspaceId ? tk.accent.fg : tk.text.secondary,
                      flexShrink: 0,
                    }}
                  >
                    <LayersOutlinedIcon sx={{ fontSize: "0.95rem" }} />
                  </Box>
                  <Box sx={{ minWidth: 0 }}>
                    <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: tk.text.primary }} noWrap>
                      {ws.name || ws.id}
                    </Typography>
                    <Typography
                      sx={{
                        fontSize: "0.68rem",
                        color: tk.text.faint,
                        fontFamily: "monospace",
                        mt: 0.25,
                      }}
                      noWrap
                      title={ws.id}
                    >
                      {shortWorkspaceId(ws.id)}
                    </Typography>
                  </Box>
                </Box>
                <Box sx={{ display: "flex", gap: 0.35, flexShrink: 0, alignItems: "center" }}>
                  <CursorIconAction
                    component={Link}
                    to={buildWorkspacePath("", "overview", { workspaceId: ws.id })}
                    onClick={() => setActiveWorkspaceId(ws.id)}
                    title={t("workspaces.open")}
                  >
                    <FolderOpenOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                  </CursorIconAction>
                  <CursorIconAction type="button" title={t("workspaces.cardMenu")} onClick={(e) => openMenu(e, ws.id)}>
                    <MoreVertOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                  </CursorIconAction>
                </Box>
              </Box>
              <Box sx={{ mt: 0.85, display: "flex", flexWrap: "wrap", gap: 0.6, alignItems: "center" }}>
                <Chip
                  label={t("workspaces.papersCount", { count: (ws.work_ids || []).length })}
                  size="small"
                  sx={{ height: 22, fontSize: "0.6875rem", border: `1px solid ${tk.border.default}`, color: tk.text.secondary, backgroundColor: tk.surface.panelAlt }}
                />
                {ws.id === targetWorkspaceId ? (
                  <Chip
                    label={t("workspaces.targetSelected")}
                    size="small"
                    sx={{
                      height: 22,
                      fontSize: "0.6875rem",
                      backgroundColor: tk.accent.chipReadyBg,
                      color: tk.accent.chipReadyFg,
                      border: `1px solid ${tk.accent.softBorder}`,
                    }}
                  />
                ) : null}
              </Box>
            </Box>
          ))}
        </Box>
      )}

      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={closeMenu}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        slotProps={{
          paper: {
            sx: {
              backgroundColor: tk.surface.panel,
              border: `1px solid ${tk.border.default}`,
            },
          },
        }}
      >
        <MenuItem
          disabled={!menuWorkspace}
          onClick={async () => {
            if (!menuWorkspace) return;
            const { id, name } = menuWorkspace;
            closeMenu();
            const nextName = await prompt({
              title: t("workspaces.renamePromptTitle"),
              label: t("workspaces.renameDialogLabel"),
              defaultValue: name || "",
              confirmLabel: t("workspaces.renameDialogSave"),
              cancelLabel: t("chat.clear.cancel"),
              validate: (v) => (!String(v).trim() ? t("workspaces.renameDialogErrorEmpty") : null),
            });
            if (nextName != null) {
              onRenameWorkspace(id, nextName);
            }
          }}
        >
          {t("workspaces.rename")}
        </MenuItem>
        <MenuItem
          disabled={!menuWorkspace}
          onClick={() => {
            if (!menuWorkspace) return;
            const id = menuWorkspace.id;
            closeMenu();
            onDeleteWorkspace(id);
          }}
          sx={{ color: tk.state.dangerFg }}
        >
          {t("workspaces.delete")}
        </MenuItem>
      </Menu>
    </Box>
  );
}
