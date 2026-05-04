import React from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";

import HubOutlinedIcon from "@mui/icons-material/HubOutlined";
import PostAddOutlinedIcon from "@mui/icons-material/PostAddOutlined";

import { CursorIconAction } from "../../components/common/index.js";
import { buildWorkspacePath } from "../WorkspacePage/utils/workContext.js";

/**
 * Single work row in the indexed corpus list (compact or comfortable density).
 */
export default function WorkspacesWorkRow({
  w,
  targetWorkspaceId,
  tk,
  t,
  viewDensity,
  onOpenWorkspace,
  onAddPaperToTarget,
}) {
  const tw = targetWorkspaceId;
  const wsUrl = tw ? buildWorkspacePath(w.work_id, "overview", { workspaceId: tw }) : buildWorkspacePath(w.work_id);

  if (viewDensity === "compact") {
    return (
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 1,
          py: 1,
          px: 1.25,
          borderRadius: "6px",
          border: `1px solid ${tk.border.default}`,
          backgroundColor: tk.surface.panel,
        }}
      >
        <Box sx={{ flex: "1 1 200px", minWidth: 0 }}>
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: tk.text.primary }} noWrap>
            {w.title || t("workspaces.row.noTitle")}
          </Typography>
          <Typography sx={{ fontSize: "0.7rem", color: tk.text.muted }} noWrap>
            {w.year != null ? `${w.year} · ` : ""}
            {w.work_id}
          </Typography>
        </Box>
        <CursorIconAction component={Link} to={wsUrl} title={t("workspaces.row.workspace")} onClick={() => onOpenWorkspace(w.work_id)}>
          <HubOutlinedIcon sx={{ fontSize: "1.05rem" }} />
        </CursorIconAction>
        <CursorIconAction type="button" title={t("workspaces.row.addToTarget")} onClick={() => onAddPaperToTarget(w.work_id)} disabled={!tw}>
          <PostAddOutlinedIcon sx={{ fontSize: "1.05rem" }} />
        </CursorIconAction>
      </Box>
    );
  }
  return (
    <Box
      sx={{
        p: 1.75,
        borderRadius: "6px",
        border: `1px solid ${tk.border.default}`,
        backgroundColor: tk.surface.panel,
      }}
    >
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: tk.text.primary }}>
        {w.title || t("workspaces.row.noTitle")}
      </Typography>
      <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, mt: 0.5 }}>
        {w.year != null ? `${w.year} · ` : ""}
        {w.work_id}
      </Typography>
      <Box sx={{ mt: 0.9, display: "flex", flexWrap: "wrap", gap: 0.75 }}>
        {w.has_semantic_layer ? (
          <Chip label={t("workspaces.chip.semanticReady")} size="small" sx={{ height: 22, fontSize: "0.6875rem" }} />
        ) : null}
      </Box>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mt: 1.25, alignItems: "center" }}>
        <CursorIconAction component={Link} to={wsUrl} title={t("workspaces.row.openInWs")} onClick={() => onOpenWorkspace(w.work_id)}>
          <HubOutlinedIcon sx={{ fontSize: "1.1rem" }} />
        </CursorIconAction>
        <CursorIconAction type="button" title={t("workspaces.row.addToTargetWs")} onClick={() => onAddPaperToTarget(w.work_id)} disabled={!tw}>
          <PostAddOutlinedIcon sx={{ fontSize: "1.1rem" }} />
        </CursorIconAction>
      </Box>
    </Box>
  );
}
