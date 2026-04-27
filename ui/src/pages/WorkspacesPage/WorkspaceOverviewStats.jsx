import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import FolderOpenOutlinedIcon from "@mui/icons-material/FolderOpenOutlined";
import LayersOutlinedIcon from "@mui/icons-material/LayersOutlined";
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined";

import { useI18n } from "../../i18n/useI18n.js";

const ICON_BY_KIND = {
  workspaces: FolderOpenOutlinedIcon,
  target: LayersOutlinedIcon,
  recent: ScheduleOutlinedIcon,
};

/**
 * @param {{
 *   stats: Array<{ id: string, kind: "workspaces" | "target" | "recent", label: string, value: string, hint: string }>,
 * }} props
 */
export default function WorkspaceOverviewStats({ stats }) {
  const { t } = useI18n();

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" },
        gap: 1,
        mb: 1.75,
      }}
    >
      {stats.map((item) => {
        const Icon = ICON_BY_KIND[item.kind] || FolderOpenOutlinedIcon;
        return (
          <Box
            key={item.id}
            sx={{
              p: 1.35,
              minWidth: 0,
              borderRadius: "6px",
              border: "1px solid rgba(255,255,255,0.08)",
              backgroundColor: "#141414",
              display: "flex",
              alignItems: "flex-start",
              gap: 1,
            }}
          >
            <Box
              sx={{
                width: 32,
                height: 32,
                borderRadius: "6px",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                border: "1px solid rgba(99,102,241,0.2)",
                backgroundColor: "rgba(99,102,241,0.08)",
                color: "rgba(129,140,248,0.95)",
                flexShrink: 0,
              }}
              aria-hidden="true"
            >
              <Icon sx={{ fontSize: "1rem" }} />
            </Box>
            <Box sx={{ minWidth: 0, flex: 1 }}>
              <Typography sx={{ fontSize: "0.6875rem", color: "rgba(255,255,255,0.46)", mb: 0.45 }}>
                {item.label}
              </Typography>
              <Typography sx={{ fontSize: "0.9rem", fontWeight: 600, color: "rgba(255,255,255,0.92)" }} noWrap title={item.value}>
                {item.value || t("workspaces.stats.targetNone")}
              </Typography>
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.52)", mt: 0.45, lineHeight: 1.45 }}>
                {item.hint}
              </Typography>
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}
