import React from "react";
import { Link } from "react-router-dom";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import ChatBubbleOutlineOutlinedIcon from "@mui/icons-material/ChatBubbleOutlineOutlined";
import DeleteOutlineOutlinedIcon from "@mui/icons-material/DeleteOutlineOutlined";
import MenuBookIcon from "@mui/icons-material/MenuBook";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CopyIdButton, CursorIconAction } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { workChatUrl, workGraphUrl, workReaderUrl } from "./workspacePageUrls.js";

/**
 * Dense document row for workspace paper list (IDE-like).
 *
 * @param {{ workspaceId?: string, workId: string, title: string, year?: number | null, doi?: string | null, arxivId?: string | null, loading?: boolean, error?: string | null, selected?: boolean, onRowActivate?: (workId: string) => void, onRemoveWork?: (workId: string) => void, rowRef?: React.Ref<HTMLDivElement | null> | ((el: HTMLDivElement | null) => void) }} props
 */
export default function WorkspacePaperRow({
  workspaceId = "",
  workId,
  title,
  year,
  doi,
  arxivId,
  loading,
  error,
  selected,
  onRowActivate,
  onRemoveWork,
  rowRef = null,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const interactive = Boolean(onRowActivate);

  const metaParts = [];
  if (year != null) metaParts.push(t("workspace.paper.yearChip", { year: String(year) }));
  if (doi) metaParts.push(`DOI ${String(doi).slice(0, 20)}${String(doi).length > 20 ? "…" : ""}`);
  if (arxivId) metaParts.push(`arXiv ${arxivId}`);
  const metaLine = metaParts.join(" · ");

  return (
    <Box
      ref={rowRef ?? undefined}
      onClick={(e) => {
        if (!onRowActivate) return;
        if (e.target instanceof Element && e.target.closest("a,button")) return;
        onRowActivate(workId);
      }}
      onKeyDown={(e) => {
        if (!onRowActivate) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onRowActivate(workId);
        }
      }}
      role={interactive ? "button" : undefined}
      tabIndex={interactive ? 0 : undefined}
      sx={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: 1.25,
        py: 1,
        px: 1.25,
        minHeight: 48,
        borderBottom: `1px solid ${tk.border.default}`,
        borderLeft: selected ? `2px solid ${tk.accent.fg}` : "2px solid transparent",
        backgroundColor: selected ? tk.accent.softBg : "transparent",
        cursor: interactive ? "pointer" : "default",
        outline: "none",
        transition: "background-color 0.12s ease, border-color 0.12s ease",
        "&:hover": {
          backgroundColor: selected ? tk.accent.emphasisHoverBg : tk.control.navItemHoverBg,
        },
        "&:hover .workspace-paper-row-actions": { opacity: 1 },
        "&:last-of-type": { borderBottom: "none" },
      }}
    >
      <Box sx={{ minWidth: 0, flex: 1 }}>
        {loading ? (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <CircularProgress size={16} sx={{ color: tk.accent.fg }} />
            <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted }}>{t("workspace.paper.loading")}</Typography>
          </Box>
        ) : null}
        {error ? (
          <Typography sx={{ fontSize: "0.75rem", color: tk.state.dangerFg, lineHeight: 1.4 }}>{error}</Typography>
        ) : null}
        {!loading && !error ? (
          <>
            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: tk.text.primary, lineHeight: 1.35 }} noWrap title={title || ""}>
              {title || t("workspace.paper.noTitle")}
            </Typography>
            {metaLine ? (
              <Typography sx={{ fontSize: "0.68rem", color: tk.text.faint, mt: 0.35 }} noWrap title={metaLine}>
                {metaLine}
              </Typography>
            ) : null}
          </>
        ) : null}
      </Box>
      {!error ? (
        <Box
          className="workspace-paper-row-actions"
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 0.35,
            flexShrink: 0,
            opacity: { xs: 1, sm: 0.72 },
            transition: "opacity 0.12s ease",
          }}
        >
          <CursorIconAction component={Link} to={workReaderUrl(workId)} title={t("workspace.tooltip.reader")}>
            <MenuBookIcon sx={{ fontSize: "1rem" }} />
          </CursorIconAction>
          <CursorIconAction component={Link} to={workGraphUrl(workId, null)} title={t("workspace.tooltip.workGraph")}>
            <AccountTreeIcon sx={{ fontSize: "1rem" }} />
          </CursorIconAction>
          <CursorIconAction component={Link} to={workChatUrl(workId, workspaceId)} title={t("workspace.tooltip.chatPaper")}>
            <ChatBubbleOutlineOutlinedIcon sx={{ fontSize: "1rem" }} />
          </CursorIconAction>
          {onRemoveWork ? (
            <CursorIconAction
              type="button"
              title={t("workspace.removePaper.tooltip")}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onRemoveWork(workId);
              }}
              sx={{ color: tk.state.dangerFg }}
            >
              <DeleteOutlineOutlinedIcon sx={{ fontSize: "1rem" }} />
            </CursorIconAction>
          ) : null}
          <CopyIdButton id={workId} tooltipCopy={t("workspace.tooltip.copyWorkId")} tooltipCopied={t("workspace.tooltip.copied")} />
        </Box>
      ) : null}
    </Box>
  );
}
