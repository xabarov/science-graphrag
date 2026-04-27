import React from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import HistoryOutlinedIcon from "@mui/icons-material/HistoryOutlined";

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
    <Box sx={{ p: 1.75, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#1a1a1a" }}>
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 1, mb: 1.25 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, minWidth: 0 }}>
          <Box
            sx={{
              width: 30,
              height: 30,
              borderRadius: "6px",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              border: "1px solid rgba(255,255,255,0.08)",
              backgroundColor: "rgba(255,255,255,0.03)",
              color: "rgba(255,255,255,0.68)",
              flexShrink: 0,
            }}
          >
            <HistoryOutlinedIcon sx={{ fontSize: "1rem" }} />
          </Box>
          <Box sx={{ minWidth: 0 }}>
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)", mb: 0.45 }}>
              {t("workspaces.recent.title")}
            </Typography>
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)", lineHeight: 1.5 }}>
              {t("workspaces.recent.desc")}
            </Typography>
          </Box>
        </Box>
        <Chip label={t("workspaces.recent.count", { count: recentWorks.length })} size="small" sx={{ height: 24, fontSize: "0.6875rem" }} />
      </Box>
      {recentWorks.length === 0 ? (
        <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("workspaces.recent.empty")}</Typography>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.9 }}>
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
                  gap: 1,
                  p: 1.1,
                  borderRadius: "6px",
                  border: "1px solid rgba(255,255,255,0.08)",
                  backgroundColor: "rgba(255,255,255,0.02)",
                  transition: "border-color 0.15s ease, background-color 0.15s ease, transform 0.15s ease",
                  "&:hover": {
                    borderColor: "rgba(255,255,255,0.14)",
                    backgroundColor: "rgba(255,255,255,0.04)",
                    transform: "translateY(-1px)",
                  },
                }}
              >
                <Box sx={{ minWidth: 0 }}>
                  <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.88)", fontWeight: 600 }} noWrap>
                    {item.title || item.workId}
                  </Typography>
                  <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.25 }} noWrap>
                    {item.workId}
                  </Typography>
                </Box>
                <CursorIconAction component={Link} to={recentOpenPath} title={t("workspaces.open")}>
                  <HubOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                </CursorIconAction>
              </Box>
            );
          })}
        </Box>
      )}
    </Box>
  );
}
