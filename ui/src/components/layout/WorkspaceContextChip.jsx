import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AddOutlinedIcon from "@mui/icons-material/AddOutlined";
import FolderOpenOutlinedIcon from "@mui/icons-material/FolderOpenOutlined";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import OpenInNewOutlinedIcon from "@mui/icons-material/OpenInNewOutlined";
import SearchOutlinedIcon from "@mui/icons-material/SearchOutlined";
import ViewListOutlinedIcon from "@mui/icons-material/ViewListOutlined";
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import InputAdornment from "@mui/material/InputAdornment";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import Popover from "@mui/material/Popover";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import { CursorIconButton } from "../common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { formatResearchApiError } from "../../services/researchApi.js";
import { createWorkspace, listWorkspaces } from "../../utils/workspaceStore.js";
import { useWorkspaceContext } from "./useWorkspaceContext.js";

function shortWorkspaceId(wsId) {
  const s = String(wsId || "").trim();
  if (!s) return "";
  if (s.length <= 14) return s;
  return `${s.slice(0, 8)}…`;
}

function workIdsLen(ws) {
  return Array.isArray(ws.work_ids) ? ws.work_ids.length : 0;
}

/**
 * @param {{ ws: { id: string, name?: string, work_ids?: string[], created_at?: string }, activeWorkspaceId: string | null, onPick: (id: string) => void, t: (k: string, v?: Record<string, string | number>) => string }} props
 */
function WorkspaceRow({ ws, activeWorkspaceId, onPick, t }) {
  const name = (ws.name || "").trim();
  const primary = name || shortWorkspaceId(ws.id);
  const showIdSubline = Boolean(name);
  const nWorks = workIdsLen(ws);
  const worksLabel = t("shell.workspaceChip.worksCount", { count: String(nWorks) });

  return (
    <ListItemButton
      title={ws.id}
      selected={ws.id === activeWorkspaceId}
      onClick={() => onPick(ws.id)}
      sx={{
        alignItems: "flex-start",
        py: 1,
        px: 1.25,
        gap: 1,
        borderRadius: 1,
        "&.Mui-selected": {
          backgroundColor: "rgba(99, 102, 241, 0.15)",
        },
        "&.Mui-selected:hover": {
          backgroundColor: "rgba(99, 102, 241, 0.22)",
        },
      }}
    >
      <FolderOpenOutlinedIcon sx={{ fontSize: "1.125rem", color: "rgba(255,255,255,0.5)", mt: 0.125, flexShrink: 0 }} />
      <Box sx={{ minWidth: 0, flex: 1 }}>
        <Typography sx={{ fontSize: "0.8125rem", fontWeight: 600, color: "rgba(255,255,255,0.92)", lineHeight: 1.25 }} noWrap>
          {primary}
        </Typography>
        {showIdSubline ? (
          <Typography
            component="div"
            sx={{
              fontSize: "0.65rem",
              fontFamily: "ui-monospace, monospace",
              color: "rgba(255,255,255,0.42)",
              mt: 0.25,
            }}
            noWrap
          >
            {shortWorkspaceId(ws.id)}
          </Typography>
        ) : null}
      </Box>
      <Typography
        sx={{
          flexShrink: 0,
          fontSize: "0.6875rem",
          fontWeight: 500,
          color: "rgba(255,255,255,0.38)",
          mt: 0.125,
          maxWidth: "5.5rem",
          textAlign: "right",
        }}
        noWrap
        title={worksLabel}
      >
        {worksLabel}
      </Typography>
    </ListItemButton>
  );
}

export default function WorkspaceContextChip() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { activeWorkspaceId, activeWorkspaceMeta, setActiveWorkspace, getLastWorkspaceHref } = useWorkspaceContext();
  const [anchorEl, setAnchorEl] = useState(null);
  const [list, setList] = useState([]);
  const [listErr, setListErr] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const searchInputRef = useRef(null);

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

  useEffect(() => {
    if (!open) return undefined;
    const id = requestAnimationFrame(() => {
      searchInputRef.current?.focus();
    });
    return () => cancelAnimationFrame(id);
  }, [open]);

  const sortedList = useMemo(() => {
    const copy = [...list];
    const aid = String(activeWorkspaceId || "").trim();
    copy.sort((a, b) => {
      if (aid && a.id === aid) return -1;
      if (aid && b.id === aid) return 1;
      const an = (a.name || "").trim().toLowerCase();
      const bn = (b.name || "").trim().toLowerCase();
      if (an && bn) return an.localeCompare(bn);
      if (an && !bn) return -1;
      if (!an && bn) return 1;
      const ad = a.created_at ? Date.parse(a.created_at) : 0;
      const bd = b.created_at ? Date.parse(b.created_at) : 0;
      return bd - ad;
    });
    return copy;
  }, [list, activeWorkspaceId]);

  const filteredList = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return sortedList;
    return sortedList.filter((ws) => {
      const name = (ws.name || "").trim().toLowerCase();
      const id = String(ws.id || "").toLowerCase();
      return name.includes(q) || id.includes(q);
    });
  }, [sortedList, searchQuery]);

  const handleClose = useCallback(() => {
    setAnchorEl(null);
    setSearchQuery("");
  }, []);

  const handlePick = useCallback(
    (id) => {
      setActiveWorkspace(id);
      navigate(`/workspace?workspace_id=${encodeURIComponent(id)}`);
      handleClose();
    },
    [setActiveWorkspace, navigate, handleClose],
  );

  const label =
    activeWorkspaceMeta?.name?.trim() ||
    (activeWorkspaceId ? t("shell.workspaceChip.unnamed") : t("shell.workspaceChip.none"));

  const listScrollSx = {
    py: 0,
    maxHeight: 260,
    overflowY: "auto",
    scrollbarWidth: "thin",
    scrollbarColor: "#2a2a2a #0a0a0a",
    "&::-webkit-scrollbar": { width: 8 },
    "&::-webkit-scrollbar-track": { backgroundColor: "#0a0a0a", borderRadius: 4 },
    "&::-webkit-scrollbar-thumb": {
      backgroundColor: "#2a2a2a",
      borderRadius: 4,
    },
    "&::-webkit-scrollbar-thumb:hover": {
      backgroundColor: "#3a3a3a",
    },
  };

  const menuTooltip = (
    <Box component="span" sx={{ display: "block", maxWidth: 280 }}>
      <Box component="span" sx={{ display: "block", lineHeight: 1.35 }}>
        {t("shell.workspaceChip.menuButtonTooltip")}
      </Box>
      {activeWorkspaceId ? (
        <Box
          component="span"
          sx={{
            display: "block",
            mt: 0.5,
            fontFamily: "ui-monospace, monospace",
            fontSize: "0.65rem",
            color: "rgba(255,255,255,0.72)",
            wordBreak: "break-all",
          }}
        >
          {activeWorkspaceId}
        </Box>
      ) : (
        <Box component="span" sx={{ display: "block", mt: 0.5, fontSize: "0.7rem", color: "rgba(255,255,255,0.55)" }}>
          {t("shell.workspaceChip.none")}
        </Box>
      )}
    </Box>
  );

  return (
    <>
      <Tooltip title={menuTooltip} describeChild>
        <ButtonBase
          type="button"
          aria-haspopup="true"
          aria-expanded={open}
          aria-label={t("shell.workspaceChip.menuButtonAria")}
          onClick={(e) => setAnchorEl(e.currentTarget)}
          disableRipple
          sx={{
            display: "inline-flex",
            alignItems: "center",
            gap: 0.625,
            pl: "10px",
            pr: "6px",
            py: "4px",
            minHeight: 28,
            maxWidth: 268,
            borderRadius: "6px",
            border: "1px solid",
            borderColor: activeWorkspaceId ? "rgba(99,102,241,0.38)" : "rgba(255,255,255,0.12)",
            backgroundColor: activeWorkspaceId ? "rgba(99,102,241,0.18)" : "rgba(255,255,255,0.05)",
            color: "rgba(255,255,255,0.92)",
            fontSize: "0.75rem",
            fontWeight: 600,
            textAlign: "left",
            transition: "border-color 0.15s ease, background-color 0.15s ease",
            "&:hover": {
              backgroundColor: activeWorkspaceId ? "rgba(99,102,241,0.26)" : "rgba(255,255,255,0.08)",
              borderColor: activeWorkspaceId ? "rgba(99,102,241,0.5)" : "rgba(255,255,255,0.18)",
            },
            "&:active": {
              transform: "scale(0.98)",
            },
            "&:hover .workspace-switcher-chevron": {
              color: "rgba(255,255,255,0.68)",
            },
          }}
        >
          <FolderOpenOutlinedIcon sx={{ fontSize: "1rem", color: "rgba(255,255,255,0.72)", flexShrink: 0 }} />
          <Typography
            component="span"
            sx={{
              flex: 1,
              minWidth: 0,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {label}
          </Typography>
          <KeyboardArrowDownIcon
            className="workspace-switcher-chevron"
            sx={{
              flexShrink: 0,
              fontSize: "1.125rem",
              color: "rgba(255,255,255,0.45)",
              transition: "transform 0.2s ease, color 0.15s ease",
              transform: open ? "rotate(-180deg)" : "none",
            }}
          />
        </ButtonBase>
      </Tooltip>
      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        slotProps={{
          paper: {
            sx: {
              minWidth: 300,
              maxWidth: 400,
              p: 1.25,
              mt: 0.75,
              backgroundColor: "#1a1a1a",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "10px",
              boxShadow: "0 10px 40px rgba(0,0,0,0.55)",
            },
          },
        }}
      >
        <Typography sx={{ fontSize: "0.6875rem", fontWeight: 700, color: "rgba(255,255,255,0.45)", px: 0.5, pb: 0.75 }}>
          {t("shell.workspaceChip.title")}
        </Typography>
        <TextField
          inputRef={searchInputRef}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder={t("shell.workspaceChip.searchPlaceholder")}
          aria-label={t("shell.workspaceChip.searchAria")}
          size="small"
          fullWidth
          variant="outlined"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchOutlinedIcon sx={{ fontSize: "1.1rem", color: "rgba(255,255,255,0.45)" }} />
              </InputAdornment>
            ),
          }}
          sx={{
            mb: 1,
            "& .MuiOutlinedInput-root": {
              fontSize: "0.8125rem",
              borderRadius: "8px",
              backgroundColor: "rgba(255,255,255,0.04)",
            },
            "& .MuiOutlinedInput-notchedOutline": {
              borderColor: "rgba(255,255,255,0.12)",
            },
            "& .MuiOutlinedInput-root:hover .MuiOutlinedInput-notchedOutline": {
              borderColor: "rgba(255,255,255,0.18)",
            },
            "& .MuiOutlinedInput-root.Mui-focused .MuiOutlinedInput-notchedOutline": {
              borderColor: "rgba(99, 102, 241, 0.5)",
              borderWidth: 1,
            },
          }}
        />
        {listErr ? (
          <Typography sx={{ fontSize: "0.75rem", color: "error.light", px: 0.5, py: 0.5 }}>{listErr}</Typography>
        ) : null}
        <List dense disablePadding sx={listScrollSx}>
          {filteredList.map((ws) => (
            <WorkspaceRow key={ws.id} ws={ws} activeWorkspaceId={activeWorkspaceId} onPick={handlePick} t={t} />
          ))}
        </List>
        {!listErr && searchQuery.trim() && sortedList.length > 0 && filteredList.length === 0 ? (
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.42)", px: 0.75, py: 1 }}>
            {t("shell.workspaceChip.searchEmpty")}
          </Typography>
        ) : null}
        <Box
          sx={{
            display: "flex",
            flexDirection: "row",
            flexWrap: "nowrap",
            alignItems: "center",
            justifyContent: "flex-end",
            gap: 0.5,
            pt: 1,
            mt: 0.5,
            borderTop: "1px solid rgba(255,255,255,0.08)",
            overflowX: "auto",
          }}
        >
          <Tooltip title={t("shell.workspaceChip.manage")}>
            <CursorIconButton component={Link} to="/workspaces" onClick={handleClose} aria-label={t("shell.workspaceChip.manage")}>
              <ViewListOutlinedIcon sx={{ fontSize: "1.05rem" }} />
            </CursorIconButton>
          </Tooltip>
          <Tooltip title={t("shell.workspaceChip.create")}>
            <CursorIconButton
              type="button"
              aria-label={t("shell.workspaceChip.create")}
              onClick={async () => {
                setListErr(null);
                try {
                  const row = await createWorkspace("Workspace");
                  if (row?.id) {
                    setActiveWorkspace(row.id);
                    navigate(`/workspace?workspace_id=${encodeURIComponent(row.id)}`);
                    handleClose();
                  }
                } catch (e) {
                  setListErr(formatResearchApiError(e));
                }
              }}
            >
              <AddOutlinedIcon sx={{ fontSize: "1.05rem" }} />
            </CursorIconButton>
          </Tooltip>
          <Tooltip title={t("shell.workspaceChip.openCurrent")}>
            <span>
              <CursorIconButton
                component={Link}
                to={getLastWorkspaceHref()}
                onClick={handleClose}
                disabled={!activeWorkspaceId}
                aria-label={t("shell.workspaceChip.openCurrent")}
              >
                <OpenInNewOutlinedIcon sx={{ fontSize: "1.05rem" }} />
              </CursorIconButton>
            </span>
          </Tooltip>
        </Box>
      </Popover>
    </>
  );
}
