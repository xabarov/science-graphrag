import React from "react";
import { Link } from "react-router-dom";
import AddOutlinedIcon from "@mui/icons-material/AddOutlined";
import OpenInNewOutlinedIcon from "@mui/icons-material/OpenInNewOutlined";
import SearchOutlinedIcon from "@mui/icons-material/SearchOutlined";
import ViewListOutlinedIcon from "@mui/icons-material/ViewListOutlined";
import Box from "@mui/material/Box";
import InputAdornment from "@mui/material/InputAdornment";
import List from "@mui/material/List";
import Popover from "@mui/material/Popover";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import { CursorIconButton } from "../common/index.js";
import { formatResearchApiError } from "../../services/researchApi.js";
import { createWorkspace } from "../../utils/workspaceStore.js";
import WorkspaceContextWorkspaceRow from "./WorkspaceContextWorkspaceRow.jsx";

/**
 * Popover listing workspaces for {@link WorkspaceContextChip}.
 */
export default function WorkspaceContextWorkspaceMenu({
  open,
  anchorEl,
  onClose,
  tk,
  theme,
  t,
  searchInputRef,
  searchQuery,
  onSearchChange,
  searchFieldSx,
  listScrollSx,
  listErr,
  filteredList,
  sortedList,
  activeWorkspaceId,
  onPickWorkspace,
  getLastWorkspaceHref,
  setListErr,
  setActiveWorkspace,
  navigate,
}) {
  return (
    <Popover
      open={open}
      anchorEl={anchorEl}
      onClose={onClose}
      anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      transformOrigin={{ vertical: "top", horizontal: "right" }}
      slotProps={{
        paper: {
          sx: {
            minWidth: 300,
            maxWidth: 400,
            p: 1.25,
            mt: 0.75,
            backgroundColor: tk.surface.panel,
            border: `1px solid ${tk.border.default}`,
            borderRadius: "10px",
            boxShadow: theme.shadows[12],
          },
        },
      }}
    >
      <Typography sx={{ fontSize: "0.6875rem", fontWeight: 700, color: tk.text.muted, px: 0.5, pb: 0.75 }}>
        {t("shell.workspaceChip.title")}
      </Typography>
      <TextField
        inputRef={searchInputRef}
        value={searchQuery}
        onChange={onSearchChange}
        placeholder={t("shell.workspaceChip.searchPlaceholder")}
        aria-label={t("shell.workspaceChip.searchAria")}
        size="small"
        fullWidth
        variant="outlined"
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchOutlinedIcon sx={{ fontSize: "1.1rem", color: tk.text.muted }} />
            </InputAdornment>
          ),
        }}
        sx={searchFieldSx}
      />
      {listErr ? (
        <Typography sx={{ fontSize: "0.75rem", color: "error.main", px: 0.5, py: 0.5 }}>{listErr}</Typography>
      ) : null}
      <List dense disablePadding sx={listScrollSx}>
        {filteredList.map((ws) => (
          <WorkspaceContextWorkspaceRow key={ws.id} ws={ws} activeWorkspaceId={activeWorkspaceId} onPick={onPickWorkspace} t={t} />
        ))}
      </List>
      {!listErr && searchQuery.trim() && sortedList.length > 0 && filteredList.length === 0 ? (
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.faint, px: 0.75, py: 1 }}>
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
          borderTop: `1px solid ${tk.border.default}`,
          overflowX: "auto",
        }}
      >
        <Tooltip title={t("shell.workspaceChip.manage")}>
          <CursorIconButton component={Link} to="/workspaces" onClick={onClose} aria-label={t("shell.workspaceChip.manage")}>
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
                  onClose();
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
              onClick={onClose}
              disabled={!activeWorkspaceId}
              aria-label={t("shell.workspaceChip.openCurrent")}
            >
              <OpenInNewOutlinedIcon sx={{ fontSize: "1.05rem" }} />
            </CursorIconButton>
          </span>
        </Tooltip>
      </Box>
    </Popover>
  );
}
