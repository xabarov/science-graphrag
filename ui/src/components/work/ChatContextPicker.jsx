import React, { useCallback, useEffect, useMemo, useState } from "react";
import ArticleOutlinedIcon from "@mui/icons-material/ArticleOutlined";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { CursorIconAction } from "../common/index.js";
import { formatWorkPrimaryLabel, formatWorkSecondaryLine, normalizeWorkListItem } from "./workListLabel.js";

const inputSx = {
  "& .MuiInputBase-input": { fontSize: "0.8125rem" },
  "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
};

const SEARCH_DEBOUNCE_MS = 280;

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
  const [anchorEl, setAnchorEl] = useState(null);
  const [articleOpen, setArticleOpen] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [searchOptions, setSearchOptions] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState(false);
  const [manualId, setManualId] = useState("");

  const summaryLabel = useMemo(() => {
    if (corpusWorkspaceOnly && String(workspaceId || "").trim()) {
      return t("chat.context.wholeWorkspace");
    }
    if (standaloneMode) {
      return t("chat.context.globalCorpus");
    }
    const w = String(workId || "").trim();
    if (!w) return t("chat.context.notSet");
    const rw = resolvedWork && String(resolvedWork.work_id ?? "").trim() === w ? resolvedWork : null;
    return formatWorkPrimaryLabel(rw || { work_id: w }, w);
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
            borderColor: "rgba(255,255,255,0.12)",
            color: "rgba(255,255,255,0.65)",
            fontSize: "0.72rem",
            "& .MuiChip-label": { px: 0.75, overflow: "hidden", textOverflow: "ellipsis" },
          }}
        />
      ) : (
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)", minWidth: 0 }} noWrap>
          {t("chat.context.current", { label: summaryLabel })}
        </Typography>
      )}
      <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)} anchorOrigin={{ vertical: "bottom", horizontal: "left" }}>
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
      {articleOpen ? (
        <Box
          sx={{
            position: "fixed",
            inset: 0,
            zIndex: 1300,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "rgba(0,0,0,0.55)",
            p: 2,
          }}
          onClick={() => setArticleOpen(false)}
        >
          <Box
            onClick={(e) => e.stopPropagation()}
            sx={{
              width: "100%",
              maxWidth: 520,
              p: 2,
              borderRadius: "6px",
              border: "1px solid rgba(255,255,255,0.1)",
              backgroundColor: "#1a1a1a",
            }}
          >
            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 1 }}>{t("chat.context.pickArticle")}</Typography>
            <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.45)", mb: 1.25 }}>{t("chat.context.searchHint")}</Typography>
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
                          color: "rgba(255,255,255,0.88)",
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
                            color: "rgba(255,255,255,0.42)",
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
              <Typography sx={{ fontSize: "0.72rem", color: "rgba(239,68,68,0.85)", mt: 1 }}>{t("chat.context.searchError")}</Typography>
            ) : null}
            <Box sx={{ mt: 2, pt: 1.5, borderTop: "1px solid rgba(255,255,255,0.08)" }}>
              <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.45)", mb: 0.75 }}>{t("chat.context.manualWorkIdHint")}</Typography>
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", alignItems: "center" }}>
                <TextField
                  size="small"
                  value={manualId}
                  onChange={(e) => setManualId(e.target.value)}
                  placeholder={t("chat.context.manualWorkIdPlaceholder")}
                  sx={{ ...inputSx, flex: "1 1 200px", minWidth: 160 }}
                />
                <Button type="button" size="small" variant="outlined" onClick={applyManualWorkId} sx={{ fontSize: "0.75rem", borderColor: "rgba(99,102,241,0.35)" }}>
                  {t("chat.context.manualApply")}
                </Button>
              </Box>
            </Box>
            <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 1, mt: 2 }}>
              <Button size="small" onClick={() => setArticleOpen(false)} sx={{ color: "rgba(255,255,255,0.65)", fontSize: "0.75rem" }}>
                {t("graph.popover.cancel")}
              </Button>
            </Box>
          </Box>
        </Box>
      ) : null}
    </Box>
  );
}
