import React from "react";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { formatWorkPrimaryLabel, formatWorkSecondaryLine, normalizeWorkListItem } from "../answer/workListLabel.js";
import { chatContextPickerButtonSx } from "./chatContextPickerConstants.js";

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   open: boolean,
 *   onClose: () => void,
 *   onArticlePicked: (item: Record<string, unknown>) => void,
 *   searchInput: string,
 *   onSearchInputChange: (v: string) => void,
 *   searchOptions: Array<Record<string, unknown>>,
 *   searchLoading: boolean,
 *   searchError: boolean,
 *   manualId: string,
 *   onManualIdChange: (v: string) => void,
 *   onApplyManualWorkId: () => void,
 *   inputSx: Record<string, unknown>,
 * }} props
 */
export function ChatContextPickerArticleDialog({
  t,
  open,
  onClose,
  onArticlePicked,
  searchInput,
  onSearchInputChange,
  searchOptions,
  searchLoading,
  searchError,
  manualId,
  onManualIdChange,
  onApplyManualWorkId,
  inputSx,
}) {
  const tk = useTheme().appTokens;
  const dialogTitleId = "chat-context-pick-article-title";

  return (
    <Dialog
      open={open}
      onClose={onClose}
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
            onSearchInputChange(v);
          }}
          getOptionLabel={(opt) => (typeof opt === "string" ? opt : formatWorkPrimaryLabel(opt))}
          isOptionEqualToValue={(a, b) => String(a?.work_id || "") === String(b?.work_id || "")}
          onChange={(_e, opt) => {
            if (opt && typeof opt === "object" && opt.work_id) {
              onArticlePicked(normalizeWorkListItem(opt));
              onClose();
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
              onChange={(e) => onManualIdChange(e.target.value)}
              placeholder={t("chat.context.manualWorkIdPlaceholder")}
              sx={{ ...inputSx, flex: "1 1 200px", minWidth: 160 }}
            />
            <Button
              type="button"
              size="small"
              variant="outlined"
              onClick={onApplyManualWorkId}
              sx={{
                ...chatContextPickerButtonSx,
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
        <Button size="small" onClick={onClose} sx={{ ...chatContextPickerButtonSx, color: tk.text.secondary }}>
          {t("chat.context.cancel")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
