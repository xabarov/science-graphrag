import React from "react";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Chip from "@mui/material/Chip";

/**
 * Graph stats chips in the workspace context strip (works / authors / internal / external citations).
 */
export default function WorkspaceStripGraphStats({ tk, t, graphStats: gs }) {
  if (!gs) return null;
  return (
    <>
      <Divider orientation="vertical" flexItem sx={{ borderColor: tk.border.default, alignSelf: "stretch", minHeight: 28, display: { xs: "none", sm: "block" } }} />
      <Stack direction="row" flexWrap="wrap" gap={0.5} useFlexGap sx={{ alignItems: "center" }}>
        <Tooltip title={t("workspace.strip.statsWorksTip")}>
          <Chip
            size="small"
            label={t("workspace.strip.statsWorks", { count: String(gs.works_count ?? "—") })}
            sx={{
              height: 24,
              fontSize: "0.6875rem",
              borderRadius: "6px",
              border: `1px solid ${tk.border.default}`,
              backgroundColor: tk.control.chipMutedBg,
              color: tk.control.chipMutedFg,
              "& .MuiChip-label": { px: 0.75, color: tk.control.chipMutedFg },
            }}
          />
        </Tooltip>
        <Tooltip title={t("workspace.strip.statsAuthorsTip")}>
          <Chip
            size="small"
            label={t("workspace.strip.statsAuthors", { count: String(gs.authors_count ?? "—") })}
            sx={{
              height: 24,
              fontSize: "0.6875rem",
              borderRadius: "6px",
              border: `1px solid ${tk.border.default}`,
              backgroundColor: tk.control.chipMutedBg,
              color: tk.control.chipMutedFg,
              "& .MuiChip-label": { px: 0.75, color: tk.control.chipMutedFg },
            }}
          />
        </Tooltip>
        <Tooltip title={t("workspace.strip.statsInternalTip")}>
          <Chip
            size="small"
            label={t("workspace.strip.statsInternal", { count: String(gs.internal_citations ?? "—") })}
            sx={{
              height: 24,
              fontSize: "0.6875rem",
              borderRadius: "6px",
              border: `1px solid ${tk.border.default}`,
              backgroundColor: tk.control.chipMutedBg,
              color: tk.control.chipMutedFg,
              "& .MuiChip-label": { px: 0.75, color: tk.control.chipMutedFg },
            }}
          />
        </Tooltip>
        <Tooltip title={t("workspace.strip.statsExternalTip")}>
          <Chip
            size="small"
            label={t("workspace.strip.statsExternal", { count: String(gs.external_citations ?? "—") })}
            sx={{
              height: 24,
              fontSize: "0.6875rem",
              borderRadius: "6px",
              border: `1px solid ${tk.border.default}`,
              backgroundColor: tk.control.chipMutedBg,
              color: tk.control.chipMutedFg,
              "& .MuiChip-label": { px: 0.75, color: tk.control.chipMutedFg },
            }}
          />
        </Tooltip>
      </Stack>
    </>
  );
}
