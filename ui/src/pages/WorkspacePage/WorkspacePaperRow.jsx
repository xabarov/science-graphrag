import React from "react";
import { Link } from "react-router-dom";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import ChatBubbleOutlineOutlinedIcon from "@mui/icons-material/ChatBubbleOutlineOutlined";
import MenuBookIcon from "@mui/icons-material/MenuBook";
import Typography from "@mui/material/Typography";

import { CopyIdButton, CursorIconAction } from "../../components/common/index.js";
import { useI18n } from "../../i18n/I18nContext.jsx";
import { workChatUrl, workGraphUrl, workReaderUrl } from "./workspacePageUrls.js";

/**
 * Dense document row for workspace paper list (IDE-like).
 *
 * @param {{ workspaceId?: string, workId: string, title: string, year?: number | null, doi?: string | null, arxivId?: string | null, loading?: boolean, error?: string | null, selected?: boolean, onRowActivate?: (workId: string) => void, rowRef?: React.Ref<HTMLDivElement | null> | ((el: HTMLDivElement | null) => void) }} props
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
  rowRef = null,
}) {
  const { t } = useI18n();
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
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        borderLeft: selected ? "2px solid rgba(129,140,248,0.85)" : "2px solid transparent",
        backgroundColor: selected ? "rgba(99,102,241,0.08)" : "transparent",
        cursor: interactive ? "pointer" : "default",
        outline: "none",
        transition: "background-color 0.12s ease, border-color 0.12s ease",
        "&:hover": {
          backgroundColor: selected ? "rgba(99,102,241,0.1)" : "rgba(255,255,255,0.03)",
        },
        "&:hover .workspace-paper-row-actions": { opacity: 1 },
        "&:last-of-type": { borderBottom: "none" },
      }}
    >
      <Box sx={{ minWidth: 0, flex: 1 }}>
        {loading ? (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <CircularProgress size={16} sx={{ color: "rgba(129,140,248,0.9)" }} />
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("workspace.paper.loading")}</Typography>
          </Box>
        ) : null}
        {error ? (
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(239,68,68,0.85)", lineHeight: 1.4 }}>{error}</Typography>
        ) : null}
        {!loading && !error ? (
          <>
            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.9)", lineHeight: 1.35 }} noWrap title={title || ""}>
              {title || t("workspace.paper.noTitle")}
            </Typography>
            {metaLine ? (
              <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.42)", mt: 0.35 }} noWrap title={metaLine}>
                {metaLine}
              </Typography>
            ) : null}
          </>
        ) : null}
      </Box>
      {!loading && !error ? (
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
          <CopyIdButton id={workId} tooltipCopy={t("workspace.tooltip.copyWorkId")} tooltipCopied={t("workspace.tooltip.copied")} />
        </Box>
      ) : null}
    </Box>
  );
}
