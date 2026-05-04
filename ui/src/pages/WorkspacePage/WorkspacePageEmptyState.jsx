import React from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Alert from "@mui/material/Alert";

import FolderOpenOutlinedIcon from "@mui/icons-material/FolderOpenOutlined";
import HomeOutlinedIcon from "@mui/icons-material/HomeOutlined";

import { CursorIconAction, CursorPrimaryButton } from "../../components/common/index.js";

/**
 * @param {{
 *   t: (k: string, v?: Record<string, string | number>) => string,
 *   theme: import("@mui/material/styles").Theme,
 *   emptyCreateBusy: boolean,
 *   emptyCreateErr: string | null,
 *   onCreateWorkspace: () => void | Promise<void>,
 * }} props
 */
export default function WorkspacePageEmptyState({ t, theme, emptyCreateBusy, emptyCreateErr, onCreateWorkspace }) {
  const tokens = theme.appTokens;
  return (
    <Box sx={{ maxWidth: 560, mt: 2 }}>
      <Alert
        severity="info"
        sx={{
          fontSize: "0.8125rem",
          mb: 2,
          bgcolor: tokens.accent.softBg,
          color: tokens.text.primary,
          "& .MuiAlert-icon": { color: tokens.accent.fg },
        }}
      >
        {t("workspace.empty.alert")}
      </Alert>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center", mb: emptyCreateErr ? 1 : 0 }}>
        <CursorPrimaryButton type="button" disabled={emptyCreateBusy} onClick={() => void onCreateWorkspace()}>
          {t("workspace.empty.createWorkspace")}
        </CursorPrimaryButton>
        <CursorIconAction component={Link} to="/workspaces" title={t("workspace.empty.workspaces")}>
          <FolderOpenOutlinedIcon sx={{ fontSize: "1.1rem" }} />
        </CursorIconAction>
        <Box component="span" sx={{ display: "inline-flex" }}>
          <CursorIconAction component={Link} to="/home" title={t("workspace.empty.about")}>
            <HomeOutlinedIcon sx={{ fontSize: "1.1rem" }} />
          </CursorIconAction>
        </Box>
      </Box>
      {emptyCreateErr ? (
        <Alert severity="error" sx={{ fontSize: "0.8125rem", mt: 1 }}>
          {emptyCreateErr}
        </Alert>
      ) : null}
    </Box>
  );
}
