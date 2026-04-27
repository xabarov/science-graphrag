import React from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";

import HubOutlinedIcon from "@mui/icons-material/HubOutlined";

import { CursorIconAction } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { buildWorkspacePath } from "../WorkspacePage/utils/workContext.js";

/**
 * @param {{
 *   recentWorks: Array<{ workId: string, title?: string, workspaceId?: string }>,
 *   fallbackWorkspaceId: string,
 * }} props
 */
export default function WorkspaceRecentPanel({ recentWorks, fallbackWorkspaceId }) {
  const { t } = useI18n();
  const tw = fallbackWorkspaceId;

  return (
    <Box
      sx={{
        p: 1.25,
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.06)",
        backgroundColor: "rgba(26,26,26,0.65)",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1, mb: 1 }}>
        <Typography sx={{ fontSize: "0.8125rem", fontWeight: 600, color: "rgba(255,255,255,0.72)" }}>
          {t("workspaces.recent.title")}
        </Typography>
        <Chip label={String(recentWorks.length)} size="small" sx={{ height: 22, fontSize: "0.6875rem", opacity: 0.85 }} />
      </Box>
      {recentWorks.length === 0 ? (
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.42)" }}>{t("workspaces.recent.empty")}</Typography>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
          {recentWorks.map((item) => {
            const wsForLink = (item.workspaceId || tw || "").trim();
            const recentOpenPath = wsForLink
              ? buildWorkspacePath(item.workId, "overview", { workspaceId: wsForLink })
              : buildWorkspacePath(item.workId);
            return (
              <Box
                key={item.workId}
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 0.75,
                  py: 0.65,
                  px: 0.75,
                  borderRadius: "6px",
                  border: "1px solid rgba(255,255,255,0.06)",
                  "&:hover": {
                    borderColor: "rgba(255,255,255,0.1)",
                    backgroundColor: "rgba(255,255,255,0.02)",
                  },
                }}
              >
                <Box sx={{ minWidth: 0 }}>
                  <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.82)", fontWeight: 500 }} noWrap>
                    {item.title || item.workId}
                  </Typography>
                  <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.35)", mt: 0.15 }} noWrap>
                    {item.workId}
                  </Typography>
                </Box>
                <CursorIconAction component={Link} to={recentOpenPath} title={t("workspaces.open")}>
                  <HubOutlinedIcon sx={{ fontSize: "1rem" }} />
                </CursorIconAction>
              </Box>
            );
          })}
        </Box>
      )}
    </Box>
  );
}
