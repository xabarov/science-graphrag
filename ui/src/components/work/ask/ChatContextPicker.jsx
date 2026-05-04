import React, { useCallback, useEffect, useMemo, useState } from "react";
import ArticleOutlinedIcon from "@mui/icons-material/ArticleOutlined";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorIconAction } from "../../common/index.js";
import { formatWorkPrimaryLabel, formatWorkSecondaryLine, normalizeWorkListItem } from "./workListLabel.js";

const SEARCH_DEBOUNCE_MS = 280;

const buttonSx = {
  textTransform: "none",
  fontSize: "0.75rem",
};

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
  const [searchInput, setSearchInput] = useState("");
  const [searchOptions, setSearchOptions] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState(false);
  const [manualId, setManualId] = useState("");

  const summaryLabel = useMemo(() => {
    const w = String(workId || "").trim();
    if (w) {
      const rw = resolvedWork && String(resolvedWork.work_id ?? "").trim() === w ? resolvedWork : null;
      return formatWorkPrimaryLabel(rw || { work_id: w }, w);
    }
    if (corpusWorkspaceOnly && String(workspaceId || "").trim()) {
      return t("chat.context.wholeWorkspace");
    }
    if (standaloneMode) {
      return t("chat.context.globalCorpus");
    }
    return t("chat.context.notSet");
  }, [corpusWorkspaceOnly, standaloneMode, t, workId, workspaceId, resolvedWork]);

  const hasWorkspace = Boolean(String(workspaceId || "").trim());
  const isComposer = variant === "composer";

  const runSearch = useCallback(
    async (q) => {
      setSearchLoading(true);
      setSearchError(false);
      try {
        const rows = await onWorkSearch(q);
        setSearchOptions(Array.isArray(rows) ? rows : []);
      } catch {
        setSearchOptions([]);
        setSearchError(true);
      } finally {
        setSearchLoading(false);
      }
    },
    [onWorkSearch],
  );

  useEffect(() => {
    if (!articleOpen) return undefined;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSearchInput("");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setManualId("");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSearchOptions([]);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSearchError(false);
    return undefined;
  }, [articleOpen]);

  useEffect(() => {
    if (!articleOpen) return undefined;
    let cancelled = false;
    const tid = setTimeout(() => {
      (async () => {
        if (cancelled) return;
        await runSearch(searchInput);
      })();
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(tid);
    };
  }, [articleOpen, searchInput, runSearch]);

  const applyManualWorkId = useCallback(() => {
    const id = String(manualId || "").trim();
    if (!id) return;
    onArticlePicked(normalizeWorkListItem({ work_id: id }, id));
    setArticleOpen(false);
    setManualId("");
  }, [manualId, onArticlePicked]);

  const dialogTitleId = "chat-context-pick-article-title";

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
            setArticleOpen(true);
          }}
        >
          {t("chat.context.pickArticle")}
        </MenuItem>
      </Menu>

      <Dialog
        open={articleOpen}
        onClose={() => setArticleOpen(false)}
        maxWidth="sm"
        fullWidth
        aria-labelledby={dialogTitleId}
        slotProps={{
          backdrop: { sx: { backgroundColor: "rgba(0,0,0,0.55)" } },
        }}
        PaperProps={{
          sx: {
            borderRadius: "6px",
            border: `1px solid ${tk.border.default}`,
            backgroundColor: tk.surface.panel,
          },
        }}
      >
        <DialogTitle id={dialogTitleId} sx={{ fontWeight: 600, fontSize: "0.8125rem", pb: 0.5 }}>
          {t("chat.context.pickArticle")}
        </DialogTitle>
        <DialogContent sx={{ pt: 1 }}>
          <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, mb: 1.25 }}>{t("chat.context.searchHint")}</Typography>
          <Autocomplete
            autoHighlight
            filterOptions={(opts) => opts}
            options={searchOptions}
            loading={searchLoading}
            value={null}
            inputValue={searchInput}
            onInputChange={(_e, v, reason) => {
              if (reason === "reset") return;
              setSearchInput(v);
            }}
            getOptionLabel={(opt) => (typeof opt === "string" ? opt : formatWorkPrimaryLabel(opt))}
            isOptionEqualToValue={(a, b) => String(a?.work_id || "") === String(b?.work_id || "")}
            onChange={(_e, opt) => {
              if (opt && typeof opt === "object" && opt.work_id) {
                onArticlePicked(normalizeWorkListItem(opt));
                setArticleOpen(false);
              }
            }}
            ListboxProps={{ sx: { maxHeight: 320 } }}
            renderInput={(params) => (
              <TextField
                {...params}
                label={t("chat.context.searchLabel")}
                size="small"
                sx={inputSx}
                autoFocus
                InputProps={{
                  ...params.InputProps,
                  endAdornment: (
                    <>
                      {searchLoading ? <CircularProgress color="inherit" size={16} sx={{ mr: 1 }} /> : null}
                      {params.InputProps.endAdornment}
                    </>
                  ),
                }}
              />
            )}
            renderOption={(props, option) => {
              const o = normalizeWorkListItem(option);
              const secondary = formatWorkSecondaryLine(o);
              return (
                <Box
                  component="li"
                  {...props}
                  key={o.work_id}
                  sx={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "flex-start",
                    justifyContent: "center",
                    width: "100%",
                    minHeight: "unset",
                    py: 0.75,
                  }}
                >
                  <Box sx={{ display: "block", width: "100%", py: 0.25 }}>
                    <Typography
                      sx={{
                        display: "block",
                        fontSize: "0.8125rem",
                        color: tk.text.primary,
                        lineHeight: 1.35,
                        whiteSpace: "normal",
                        wordBreak: "break-word",
                      }}
                    >
                      {formatWorkPrimaryLabel(o)}
                    </Typography>
                    {secondary ? (
                      <Typography
                        sx={{
                          display: "block",
                          fontSize: "0.68rem",
                          color: tk.text.muted,
                          mt: 0.25,
                          lineHeight: 1.35,
                          whiteSpace: "normal",
                          wordBreak: "break-word",
                        }}
                      >
                        {secondary}
                      </Typography>
                    ) : null}
                  </Box>
                </Box>
              );
            }}
            noOptionsText={searchLoading ? t("chat.context.searchLoading") : searchError ? t("chat.context.searchError") : t("chat.context.searchEmpty")}
          />
          {searchError ? (
            <Typography sx={{ fontSize: "0.72rem", color: tk.state.dangerFg, mt: 1 }}>{t("chat.context.searchError")}</Typography>
          ) : null}
          <Box sx={{ mt: 2, pt: 1.5, borderTop: `1px solid ${tk.border.default}` }}>
            <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, mb: 0.75 }}>{t("chat.context.manualWorkIdHint")}</Typography>
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", alignItems: "center" }}>
              <TextField
                size="small"
                value={manualId}
                onChange={(e) => setManualId(e.target.value)}
                placeholder={t("chat.context.manualWorkIdPlaceholder")}
                sx={{ ...inputSx, flex: "1 1 200px", minWidth: 160 }}
              />
              <Button
                type="button"
                size="small"
                variant="outlined"
                onClick={applyManualWorkId}
                sx={{
                  ...buttonSx,
                  borderColor: tk.accent.softBorder,
                  color: tk.accent.fg,
                }}
              >
                {t("chat.context.manualApply")}
              </Button>
            </Box>
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 2, pb: 2, pt: 0 }}>
          <Button size="small" onClick={() => setArticleOpen(false)} sx={{ ...buttonSx, color: tk.text.secondary }}>
            {t("chat.context.cancel")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
