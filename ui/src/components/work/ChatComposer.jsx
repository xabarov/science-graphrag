import React, { useCallback } from "react";
import { Link } from "react-router-dom";
import KeyboardArrowUpRoundedIcon from "@mui/icons-material/KeyboardArrowUpRounded";
import OpenInNewOutlinedIcon from "@mui/icons-material/OpenInNewOutlined";
import Box from "@mui/material/Box";
import FormControl from "@mui/material/FormControl";
import IconButton from "@mui/material/IconButton";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

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
}) {
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
          borderRadius: "10px",
          border: "1px solid rgba(255,255,255,0.14)",
          backgroundColor: "rgba(0,0,0,0.28)",
          p: 1.1,
          display: "flex",
          flexDirection: "column",
          gap: 0.75,
          transition: "border-color 0.15s ease, box-shadow 0.15s ease",
          "&:focus-within": {
            borderColor: "rgba(99,102,241,0.45)",
            boxShadow: "0 0 0 1px rgba(99,102,241,0.2)",
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
        <Box sx={{ px: 0.5, display: "flex", alignItems: "center", flexWrap: "wrap", gap: 1 }}>
          <FormControl size="small" variant="standard" sx={{ minWidth: 168, maxWidth: "100%" }}>
            <InputLabel id="chat-answer-mode-label" sx={{ fontSize: "0.8125rem" }}>
              {t("chat.answerMode.label")}
            </InputLabel>
            <Select
              labelId="chat-answer-mode-label"
              value={answerClassHint || ""}
              label={t("chat.answerMode.label")}
              onChange={(e) => onAnswerClassHintChange?.(String(e.target.value))}
              sx={{ fontSize: "0.8125rem" }}
            >
              {ANSWER_CLASS_HINT_OPTIONS.map((o) => (
                <MenuItem key={o.value || "auto"} value={o.value} sx={{ fontSize: "0.8125rem" }}>
                  {t(o.labelKey)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
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
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1, flexWrap: "wrap", pr: 0.25 }}>
          <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.35)", flex: "1 1 140px" }}>{t("chat.composer.enterHint")}</Typography>
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 0.25 }}>
            {inWorkspace && !locked ? (
              <IconButton
                type="button"
                component={Link}
                to={standaloneChatPath}
                size="small"
                aria-label={t("chat.composer.openStandaloneAria")}
                title={t("chat.composer.openStandaloneAria")}
                sx={{ color: "rgba(255,255,255,0.38)" }}
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
