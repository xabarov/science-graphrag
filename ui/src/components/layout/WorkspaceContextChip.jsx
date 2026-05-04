import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import FolderOpenOutlinedIcon from "@mui/icons-material/FolderOpenOutlined";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Typography from "@mui/material/Typography";
import Tooltip from "@mui/material/Tooltip";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../i18n/useI18n.js";
import { outlinedAppTextFieldSx } from "../../theme/settingsFormSx.js";
import { formatResearchApiError } from "../../services/researchApi.js";
import { listWorkspaces } from "../../utils/workspaceStore.js";
import { useWorkspaceContext } from "./useWorkspaceContext.js";
import WorkspaceContextWorkspaceMenu from "./WorkspaceContextWorkspaceMenu.jsx";

export default function WorkspaceContextChip() {
  const { t } = useI18n();
  const theme = useTheme();
  const tk = theme.appTokens;
  const navigate = useNavigate();
  const { activeWorkspaceId, activeWorkspaceMeta, setActiveWorkspace, getLastWorkspaceHref } = useWorkspaceContext();
  const [anchorEl, setAnchorEl] = useState(null);
  const [list, setList] = useState([]);
  const [listErr, setListErr] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const searchInputRef = useRef(null);

  const open = Boolean(anchorEl);
  const isLight = theme.palette.mode === "light";

  const searchFieldSx = useMemo(
    () => ({
      ...outlinedAppTextFieldSx(tk),
      mb: 1,
      "& .MuiOutlinedInput-root": {
        fontSize: "0.8125rem",
        borderRadius: "8px",
        backgroundColor: tk.control.outlinedBg,
      },
      "& .MuiOutlinedInput-notchedOutline": {
        borderColor: tk.border.strong,
      },
      "& .MuiOutlinedInput-root:hover .MuiOutlinedInput-notchedOutline": {
        borderColor: tk.control.outlinedBorderHover,
      },
      "& .MuiOutlinedInput-root.Mui-focused .MuiOutlinedInput-notchedOutline": {
        borderColor: "rgba(99, 102, 241, 0.5)",
        borderWidth: 1,
      },
    }),
    [tk],
  );

  const listScrollSx = useMemo(
    () => ({
      py: 0,
      maxHeight: 260,
      overflowY: "auto",
      scrollbarWidth: "thin",
      scrollbarColor: isLight ? "#cbd5e1 #f5f7fb" : "#2a2a2a #0a0a0a",
      "&::-webkit-scrollbar": { width: 8 },
      "&::-webkit-scrollbar-track": {
        backgroundColor: isLight ? "#f5f7fb" : "#0a0a0a",
        borderRadius: 4,
      },
      "&::-webkit-scrollbar-thumb": {
        backgroundColor: isLight ? "#cbd5e1" : "#2a2a2a",
        borderRadius: 4,
      },
      "&::-webkit-scrollbar-thumb:hover": {
        backgroundColor: isLight ? "#94a3b8" : "#3a3a3a",
      },
    }),
    [isLight],
  );

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

  const menuTooltip = (
    <Box component="span" sx={{ display: "block", maxWidth: 280 }}>
      <Box component="span" sx={{ display: "block", lineHeight: 1.35, color: tk.text.primary }}>
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
            color: tk.text.secondary,
            wordBreak: "break-all",
          }}
        >
          {activeWorkspaceId}
        </Box>
      ) : (
        <Box component="span" sx={{ display: "block", mt: 0.5, fontSize: "0.7rem", color: tk.text.muted }}>
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
            borderColor: activeWorkspaceId ? tk.accent.softBorder : tk.border.strong,
            backgroundColor: activeWorkspaceId ? tk.accent.softBg : tk.control.outlinedBg,
            color: tk.text.primary,
            fontSize: "0.75rem",
            fontWeight: 600,
            textAlign: "left",
            transition: "border-color 0.15s ease, background-color 0.15s ease",
            "&:hover": {
              backgroundColor: activeWorkspaceId ? tk.accent.emphasisHoverBg : tk.control.outlinedBgHover,
              borderColor: activeWorkspaceId ? tk.accent.emphasisHoverBorder : tk.control.outlinedBorderHover,
            },
            "&:active": {
              transform: "scale(0.98)",
            },
            "&:hover .workspace-switcher-chevron": {
              color: tk.text.secondary,
            },
          }}
        >
          <FolderOpenOutlinedIcon sx={{ fontSize: "1rem", color: tk.text.secondary, flexShrink: 0 }} />
          <Typography
            component="span"
            sx={{
              flex: 1,
              minWidth: 0,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              color: "inherit",
            }}
          >
            {label}
          </Typography>
          <KeyboardArrowDownIcon
            className="workspace-switcher-chevron"
            sx={{
              flexShrink: 0,
              fontSize: "1.125rem",
              color: tk.text.muted,
              transition: "transform 0.2s ease, color 0.15s ease",
              transform: open ? "rotate(-180deg)" : "none",
            }}
          />
        </ButtonBase>
      </Tooltip>
      <WorkspaceContextWorkspaceMenu
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        tk={tk}
        theme={theme}
        t={t}
        searchInputRef={searchInputRef}
        searchQuery={searchQuery}
        onSearchChange={(e) => setSearchQuery(e.target.value)}
        searchFieldSx={searchFieldSx}
        listScrollSx={listScrollSx}
        listErr={listErr}
        filteredList={filteredList}
        sortedList={sortedList}
        activeWorkspaceId={activeWorkspaceId}
        onPickWorkspace={handlePick}
        getLastWorkspaceHref={getLastWorkspaceHref}
        setListErr={setListErr}
        setActiveWorkspace={setActiveWorkspace}
        navigate={navigate}
      />
    </>
  );
}
