import React, { useCallback, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import AutoAwesomeOutlinedIcon from "@mui/icons-material/AutoAwesomeOutlined";
import KeyboardArrowUpRoundedIcon from "@mui/icons-material/KeyboardArrowUpRounded";
import OpenInNewOutlinedIcon from "@mui/icons-material/OpenInNewOutlined";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { CursorIconAction } from "../common/index.js";
import { ChatContextPicker } from "./ChatContextPicker.jsx";

const ANSWER_CLASS_HINT_OPTIONS = [
  { value: "", labelKey: "chat.answerMode.auto" },
  { value: "inventory", labelKey: "chat.answerMode.inventory" },
  { value: "fact_lookup", labelKey: "chat.answerMode.fact_lookup" },
  { value: "grounded_explanation", labelKey: "chat.answerMode.grounded_explanation" },
  { value: "relation_tracing", labelKey: "chat.answerMode.relation_tracing" },
  { value: "quote_extraction", labelKey: "chat.answerMode.quote_extraction" },
  { value: "ideation", labelKey: "chat.answerMode.ideation" },
  { value: "bibliography_export", labelKey: "chat.answerMode.bibliography_export" },
  { value: "synthesis", labelKey: "chat.answerMode.synthesis" },
];

const inputSx = {
  "& .MuiInputBase-input": { fontSize: "0.8125rem", py: 0.75 },
  "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
};

/**
 * Bottom composer (GPT-like): bordered input + context icon + send arrow-up.
 *
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   query: string,
 *   onQueryChange: (v: string) => void,
 *   loading: boolean,
 *   onSubmit: (e: React.FormEvent) => void,
 *   inWorkspace: boolean,
 *   standaloneChatPath: string,
 *   locked: boolean,
 *   scopedWorkId?: string | null,
 *   workspaceId?: string,
 *   workId?: string,
 *   onWorkIdChange?: (v: string) => void,
 *   onArticlePicked?: (item: Record<string, unknown>) => void,
 *   onWorkSearch?: (q: string) => Promise<Array<Record<string, unknown>>>,
 *   resolvedWork?: Record<string, unknown> | null,
 *   corpusWorkspaceOnly?: boolean,
 *   standaloneMode?: boolean,
 *   answerClassHint?: string,
 *   onAnswerClassHintChange?: (v: string) => void,
 *   streamingHint?: string,
 * }} props
 */
export function ChatComposer({
  t,
  query,
  onQueryChange,
  loading,
  onSubmit,
  inWorkspace,
  standaloneChatPath,
  locked,
  scopedWorkId = "",
  workspaceId = "",
  workId = "",
  onWorkIdChange,
  onArticlePicked,
  onWorkSearch,
  resolvedWork = null,
  corpusWorkspaceOnly = false,
  standaloneMode = false,
  answerClassHint = "",
  onAnswerClassHintChange,
  streamingHint = "",
}) {
  const [modeAnchorEl, setModeAnchorEl] = useState(null);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key !== "Enter" || e.shiftKey) return;
      if (e.nativeEvent.isComposing) return;
      e.preventDefault();
      if (loading || !String(query || "").trim()) return;
      const form = e.currentTarget.closest("form");
      if (form instanceof HTMLFormElement) form.requestSubmit();
    },
    [loading, query],
  );

  const selectedAnswerMode = useMemo(
    () => ANSWER_CLASS_HINT_OPTIONS.find((option) => option.value === String(answerClassHint || "").trim()) || ANSWER_CLASS_HINT_OPTIONS[0],
    [answerClassHint],
  );
  const selectedAnswerModeLabel = t(selectedAnswerMode.labelKey);
  const answerModeMenuOpen = Boolean(modeAnchorEl);

  return (
    <Box
      component="form"
      onSubmit={onSubmit}
      sx={{
        mt: "auto",
        pt: 1.25,
        flexShrink: 0,
        width: "100%",
        maxWidth: "min(920px, 100%)",
        mx: "auto",
      }}
    >
      <Box
        sx={{
          borderRadius: "6px",
          border: "1px solid rgba(255,255,255,0.12)",
          backgroundColor: "#1a1a1a",
          p: 1.1,
          display: "flex",
          flexDirection: "column",
          gap: 0.75,
          transition: "border-color 0.15s ease, background-color 0.15s ease",
          "&:focus-within": {
            borderColor: "rgba(99,102,241,0.45)",
            backgroundColor: "rgba(26,26,26,0.98)",
          },
        }}
      >
        {locked ? (
          <Box sx={{ px: 0.5, pt: 0.25, display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
            <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.45)" }}>{t("askPanel.workIdScopeLabel")}</Typography>
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.82)", fontFamily: "monospace" }}>{String(scopedWorkId || workId).trim()}</Typography>
          </Box>
        ) : (
          <ChatContextPicker
            variant="composer"
            t={t}
            workspaceId={workspaceId}
            workId={workId}
            onWorkIdChange={onWorkIdChange || (() => {})}
            onArticlePicked={onArticlePicked || (() => {})}
            onWorkSearch={onWorkSearch || (async () => [])}
            resolvedWork={resolvedWork}
            corpusWorkspaceOnly={corpusWorkspaceOnly}
            standaloneMode={standaloneMode}
          />
        )}
        {loading && streamingHint ? (
          <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.45)", px: 0.5 }}>{streamingHint}</Typography>
        ) : null}
        <TextField
          placeholder={t("chat.composer.placeholder")}
          value={query}
          onChange={(ev) => onQueryChange(ev.target.value)}
          onKeyDown={handleKeyDown}
          multiline
          minRows={2}
          maxRows={8}
          fullWidth
          size="small"
          variant="standard"
          InputProps={{ disableUnderline: true }}
          sx={{ ...inputSx, px: 0.5 }}
        />
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 1,
            flexWrap: "wrap",
            pr: 0.25,
            pt: 0.15,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.65, flexWrap: "wrap", minWidth: 0, flex: "1 1 240px" }}>
            <CursorIconAction
              title={t("chat.answerMode.openMenuAria")}
              aria-label={t("chat.answerMode.openMenuAria")}
              onClick={(e) => setModeAnchorEl(e.currentTarget)}
              sx={
                selectedAnswerMode.value
                  ? {
                      color: "rgba(129,140,248,0.95)",
                      borderColor: "rgba(99,102,241,0.3)",
                      backgroundColor: "rgba(99,102,241,0.12)",
                      "&:hover": {
                        backgroundColor: "rgba(99,102,241,0.18)",
                        borderColor: "rgba(99,102,241,0.42)",
                        color: "rgba(129,140,248,0.98)",
                      },
                    }
                  : null
              }
            >
              <AutoAwesomeOutlinedIcon sx={{ fontSize: "1rem" }} />
            </CursorIconAction>
            <Typography
              sx={{
                fontSize: "0.72rem",
                color: selectedAnswerMode.value ? "rgba(129,140,248,0.95)" : "rgba(255,255,255,0.52)",
                minWidth: 0,
                maxWidth: "min(260px, 50vw)",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
              title={t("chat.answerMode.currentLabel", { label: selectedAnswerModeLabel })}
            >
              {selectedAnswerModeLabel}
            </Typography>
            <Menu
              anchorEl={modeAnchorEl}
              open={answerModeMenuOpen}
              onClose={() => setModeAnchorEl(null)}
              anchorOrigin={{ vertical: "top", horizontal: "left" }}
              transformOrigin={{ vertical: "bottom", horizontal: "left" }}
              PaperProps={{
                sx: {
                  mt: -0.75,
                  minWidth: 240,
                  borderRadius: "6px",
                  border: "1px solid rgba(255,255,255,0.08)",
                  backgroundColor: "#1a1a1a",
                  boxShadow: "none",
                  backgroundImage: "none",
                },
              }}
              MenuListProps={{ "aria-label": t("chat.answerMode.label") }}
            >
              {ANSWER_CLASS_HINT_OPTIONS.map((option) => {
                const selected = option.value === selectedAnswerMode.value;
                return (
                  <MenuItem
                    key={option.value || "auto"}
                    selected={selected}
                    onClick={() => {
                      onAnswerClassHintChange?.(option.value);
                      setModeAnchorEl(null);
                    }}
                    sx={{
                      fontSize: "0.8125rem",
                      minHeight: 34,
                      color: selected ? "rgba(255,255,255,0.94)" : "rgba(255,255,255,0.76)",
                      "&.Mui-selected": {
                        backgroundColor: "rgba(99,102,241,0.12)",
                      },
                      "&.Mui-selected:hover": {
                        backgroundColor: "rgba(99,102,241,0.16)",
                      },
                    }}
                  >
                    {t(option.labelKey)}
                  </MenuItem>
                );
              })}
            </Menu>
            <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.35)", flex: "0 1 auto" }}>
              {t("chat.composer.enterHint")}
            </Typography>
          </Box>
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 0.35 }}>
            {inWorkspace && !locked ? (
              <IconButton
                type="button"
                component={Link}
                to={standaloneChatPath}
                size="small"
                aria-label={t("chat.composer.openStandaloneAria")}
                title={t("chat.composer.openStandaloneAria")}
                sx={{
                  color: "rgba(255,255,255,0.38)",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: "6px",
                  "&:hover": { backgroundColor: "rgba(255,255,255,0.04)" },
                }}
              >
                <OpenInNewOutlinedIcon sx={{ fontSize: "1rem" }} />
              </IconButton>
            ) : null}
            <IconButton
              type="submit"
              size="small"
              disabled={loading || !String(query || "").trim()}
              aria-label={loading ? t("chat.composer.sending") : t("chat.composer.sendAria")}
              title={loading ? t("chat.composer.sending") : t("chat.composer.sendAria")}
              sx={{
                color: "rgba(129,140,248,0.95)",
                backgroundColor: "rgba(99,102,241,0.18)",
                border: "1px solid rgba(99,102,241,0.42)",
                "&:hover": { backgroundColor: "rgba(99,102,241,0.26)" },
                "&.Mui-disabled": { color: "rgba(255,255,255,0.22)", borderColor: "rgba(255,255,255,0.08)" },
              }}
            >
              <KeyboardArrowUpRoundedIcon sx={{ fontSize: "1.25rem" }} />
            </IconButton>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
