import React, { useCallback, useMemo, useState } from "react";
import ArticleOutlinedIcon from "@mui/icons-material/ArticleOutlined";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorIconAction } from "../../../common/index.js";
import { normalizeWorkListItem } from "../answer/workListLabel.js";
import { deriveChatContextSummaryLabel } from "./chatContextPickerModel.js";
import { ChatContextPickerArticleDialog } from "./ChatContextPickerArticleDialog.jsx";
import { useChatContextArticleSearch } from "./useChatContextArticleSearch.js";

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   workspaceId: string,
 *   workId: string,
 *   onWorkIdChange: (id: string) => void,
 *   onArticlePicked: (item: Record<string, unknown>) => void,
 *   onWorkSearch: (q: string) => Promise<Array<Record<string, unknown>>>,
 *   resolvedWork: Record<string, unknown> | null,
 *   corpusWorkspaceOnly: boolean,
 *   standaloneMode: boolean,
 *   variant?: "default" | "composer",
 * }} props
 */
export function ChatContextPicker({
  t,
  workspaceId,
  workId,
  onWorkIdChange,
  onArticlePicked,
  onWorkSearch,
  resolvedWork,
  corpusWorkspaceOnly,
  standaloneMode,
  variant = "default",
}) {
  const tk = useTheme().appTokens;
  const inputSx = useMemo(
    () => ({
      "& .MuiInputBase-input": { fontSize: "0.8125rem" },
      "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: tk.text.secondary },
    }),
    [tk.text.secondary],
  );

  const [anchorEl, setAnchorEl] = useState(null);
  const [articleOpen, setArticleOpen] = useState(false);
  const [manualId, setManualId] = useState("");

  const {
    searchInput,
    setSearchInput,
    searchOptions,
    searchLoading,
    searchError,
  } = useChatContextArticleSearch({ onWorkSearch, articleOpen });

  const summaryLabel = useMemo(
    () =>
      deriveChatContextSummaryLabel(
        { workId, resolvedWork, corpusWorkspaceOnly, standaloneMode, workspaceId },
        t,
      ),
    [corpusWorkspaceOnly, standaloneMode, t, workId, workspaceId, resolvedWork],
  );

  const hasWorkspace = Boolean(String(workspaceId || "").trim());
  const isComposer = variant === "composer";

  const applyManualWorkId = useCallback(() => {
    const id = String(manualId || "").trim();
    if (!id) return;
    onArticlePicked(normalizeWorkListItem({ work_id: id }, id));
    setArticleOpen(false);
    setManualId("");
  }, [manualId, onArticlePicked]);

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 0.75,
        flexWrap: "wrap",
        minWidth: 0,
        ...(isComposer ? {} : { mb: 1 }),
      }}
    >
      <CursorIconAction aria-label={t("chat.context.pickerAria")} title={t("chat.context.pickerAria")} onClick={(e) => setAnchorEl(e.currentTarget)}>
        <ArticleOutlinedIcon sx={{ fontSize: "1.05rem" }} />
      </CursorIconAction>
      {isComposer ? (
        <Chip
          size="small"
          variant="outlined"
          label={summaryLabel}
          title={t("chat.context.current", { label: summaryLabel })}
          sx={{
            height: 22,
            maxWidth: "min(280px, 52vw)",
            borderColor: tk.border.default,
            color: tk.text.secondary,
            fontSize: "0.72rem",
            "& .MuiChip-label": { px: 0.75, overflow: "hidden", textOverflow: "ellipsis" },
          }}
        />
      ) : (
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, minWidth: 0 }} noWrap>
          {t("chat.context.current", { label: summaryLabel })}
        </Typography>
      )}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={
          isComposer ? { vertical: "top", horizontal: "left" } : { vertical: "bottom", horizontal: "left" }
        }
        transformOrigin={
          isComposer ? { vertical: "bottom", horizontal: "left" } : { vertical: "top", horizontal: "left" }
        }
      >
        {hasWorkspace ? (
          <MenuItem
            dense
            onClick={() => {
              onWorkIdChange("");
              setAnchorEl(null);
            }}
          >
            {t("chat.context.wholeWorkspace")}
          </MenuItem>
        ) : null}
        {standaloneMode ? (
          <MenuItem
            dense
            onClick={() => {
              onWorkIdChange("");
              setAnchorEl(null);
            }}
          >
            {t("chat.context.globalCorpus")}
          </MenuItem>
        ) : null}
        <MenuItem
          dense
          onClick={() => {
            setAnchorEl(null);
            setManualId("");
            setArticleOpen(true);
          }}
        >
          {t("chat.context.pickArticle")}
        </MenuItem>
      </Menu>

      <ChatContextPickerArticleDialog
        t={t}
        open={articleOpen}
        onClose={() => setArticleOpen(false)}
        onArticlePicked={onArticlePicked}
        searchInput={searchInput}
        onSearchInputChange={setSearchInput}
        searchOptions={searchOptions}
        searchLoading={searchLoading}
        searchError={searchError}
        manualId={manualId}
        onManualIdChange={setManualId}
        onApplyManualWorkId={applyManualWorkId}
        inputSx={inputSx}
      />
    </Box>
  );
}
