import React from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/I18nContext.jsx";
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
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mb: 0.75 }}>{t("workspaces.recent.title")}</Typography>
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
              <Box key={item.workId} sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1 }}>
                <Box sx={{ minWidth: 0 }}>
                  <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)", fontWeight: 600 }}>
                    {item.title || item.workId}
                  </Typography>
                  <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.25 }}>{item.workId}</Typography>
                </Box>
                <CursorSmallButton component={Link} to={recentOpenPath} sx={{ textDecoration: "none" }}>
                  {t("workspaces.open")}
                </CursorSmallButton>
              </Box>
            );
          })}
        </Box>
      )}
    </Box>
  );
}
