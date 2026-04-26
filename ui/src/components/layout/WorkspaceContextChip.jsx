import React, { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import FolderOpenOutlinedIcon from "@mui/icons-material/FolderOpenOutlined";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Popover from "@mui/material/Popover";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../common/index.js";
import { useI18n } from "../../i18n/I18nContext.jsx";
import { formatResearchApiError } from "../../services/researchApi.js";
import { createWorkspace, listWorkspaces } from "../../utils/workspaceStore.js";
import { useWorkspaceContext } from "./WorkspaceContext.jsx";

export default function WorkspaceContextChip() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { activeWorkspaceId, activeWorkspaceMeta, setActiveWorkspace, getLastWorkspaceHref } = useWorkspaceContext();
  const [anchorEl, setAnchorEl] = useState(null);
  const [list, setList] = useState([]);
  const [listErr, setListErr] = useState(null);

  const open = Boolean(anchorEl);

  const refreshList = useCallback(async () => {
    setListErr(null);
    try {
      const items = await listWorkspaces();
      setList(Array.isArray(items) ? items : []);
    } catch (e) {
      setListErr(formatResearchApiError(e));
      setList([]);
    }
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    const id = requestAnimationFrame(() => {
      void refreshList();
    });
    return () => cancelAnimationFrame(id);
  }, [open, refreshList]);

  const label =
    activeWorkspaceMeta?.name?.trim() ||
    (activeWorkspaceId ? t("shell.workspaceChip.unnamed") : t("shell.workspaceChip.none"));

  function shortWorkspaceId(wsId) {
    const s = String(wsId || "").trim();
    if (!s) return "";
    if (s.length <= 14) return s;
    return `${s.slice(0, 8)}…`;
  }

  return (
    <>
      <Tooltip title={activeWorkspaceId ? `${t("shell.workspaceChip.title")}: ${activeWorkspaceId}` : t("shell.workspaceChip.none")}>
        <Chip
          size="small"
          icon={<FolderOpenOutlinedIcon sx={{ fontSize: "1rem !important", color: "rgba(255,255,255,0.75) !important" }} />}
          label={label}
          onClick={(e) => setAnchorEl(e.currentTarget)}
          sx={{
            maxWidth: 220,
            height: 28,
            fontWeight: 600,
            fontSize: "0.75rem",
            backgroundColor: activeWorkspaceId ? "rgba(99,102,241,0.22)" : "rgba(255,255,255,0.08)",
            color: "rgba(255,255,255,0.92)",
            "& .MuiChip-label": { overflow: "hidden", textOverflow: "ellipsis" },
            "& .MuiChip-icon": { marginLeft: "6px" },
          }}
          variant="outlined"
        />
      </Tooltip>
      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
        transformOrigin={{ vertical: "top", horizontal: "left" }}
        slotProps={{ paper: { sx: { minWidth: 280, maxWidth: 360, p: 1, backgroundColor: "#141414", border: "1px solid rgba(255,255,255,0.1)" } } }}
      >
        <Typography sx={{ fontSize: "0.6875rem", fontWeight: 700, color: "rgba(255,255,255,0.45)", px: 1, py: 0.5 }}>
          {t("shell.workspaceChip.title")}
        </Typography>
        {listErr ? (
          <Typography sx={{ fontSize: "0.75rem", color: "error.light", px: 1, py: 0.5 }}>{listErr}</Typography>
        ) : null}
        <List dense sx={{ py: 0, maxHeight: 280, overflow: "auto" }}>
          {list.map((ws) => (
            <ListItemButton
              key={ws.id}
              title={ws.id}
              selected={ws.id === activeWorkspaceId}
              onClick={() => {
                setActiveWorkspace(ws.id);
                navigate(`/workspace?workspace_id=${encodeURIComponent(ws.id)}`);
                setAnchorEl(null);
              }}
            >
              <ListItemText
                primary={ws.name || shortWorkspaceId(ws.id)}
                secondary={shortWorkspaceId(ws.id)}
                primaryTypographyProps={{ sx: { fontSize: "0.8125rem", fontWeight: 600 } }}
                secondaryTypographyProps={{
                  sx: { fontSize: "0.65rem", fontFamily: "monospace", color: "rgba(255,255,255,0.42)" },
                }}
              />
            </ListItemButton>
          ))}
        </List>
        <Divider sx={{ borderColor: "rgba(255,255,255,0.08)", my: 0.5 }} />
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, px: 1, py: 1 }}>
          <CursorSmallButton
            component={Link}
            to="/workspaces"
            onClick={() => setAnchorEl(null)}
            sx={{ textDecoration: "none", fontSize: "0.75rem" }}
          >
            {t("shell.workspaceChip.manage")}
          </CursorSmallButton>
          <CursorSmallButton
            type="button"
            sx={{ fontSize: "0.75rem" }}
            onClick={async () => {
              setListErr(null);
              try {
                const row = await createWorkspace("Workspace");
                if (row?.id) {
                  setActiveWorkspace(row.id);
                  navigate(`/workspace?workspace_id=${encodeURIComponent(row.id)}`);
                  setAnchorEl(null);
                }
              } catch (e) {
                setListErr(formatResearchApiError(e));
              }
            }}
          >
            {t("shell.workspaceChip.create")}
          </CursorSmallButton>
          <CursorSmallButton
            component={Link}
            to={getLastWorkspaceHref()}
            onClick={() => setAnchorEl(null)}
            sx={{ textDecoration: "none", fontSize: "0.75rem" }}
            disabled={!activeWorkspaceId}
          >
            {t("shell.workspaceChip.openCurrent")}
          </CursorSmallButton>
        </Box>
      </Popover>
    </>
  );
}
