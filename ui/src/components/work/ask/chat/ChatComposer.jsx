import React, { useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import PublicOutlinedIcon from "@mui/icons-material/PublicOutlined";
import DeleteSweepOutlinedIcon from "@mui/icons-material/DeleteSweepOutlined";
import KeyboardArrowUpRoundedIcon from "@mui/icons-material/KeyboardArrowUpRounded";
import OpenInNewOutlinedIcon from "@mui/icons-material/OpenInNewOutlined";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { ChatContextPicker } from "./ChatContextPicker.jsx";

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
 *   streamingHint?: string,
 *   onClearChatClick?: () => void,
 *   clearChatDisabled?: boolean,
 *   structuredAnswerPending?: boolean,
 *   webResearchEnabled?: boolean,
 *   onWebResearchEnabledChange?: (v: boolean) => void,
 *   agentMode?: "agent" | "plan",
 *   onAgentModeChange?: (m: "agent" | "plan") => void,
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
  streamingHint = "",
  onClearChatClick,
  clearChatDisabled = false,
  structuredAnswerPending = false,
  webResearchEnabled = false,
  onWebResearchEnabledChange,
  agentMode = "agent",
  onAgentModeChange,
}) {
  const tk = useTheme().appTokens;

  const inputSx = useMemo(
    () => ({
      "& .MuiInputBase-input": { fontSize: "0.8125rem", py: 0.75 },
      "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: tk.text.secondary },
    }),
    [tk],
  );

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key !== "Enter" || e.shiftKey) return;
      if (e.nativeEvent.isComposing) return;
      e.preventDefault();
      if (loading || structuredAnswerPending || !String(query || "").trim()) return;
      const form = e.currentTarget.closest("form");
      if (form instanceof HTMLFormElement) form.requestSubmit();
    },
    [loading, query, structuredAnswerPending],
  );

  const handleAgentModeChange = useCallback(
    (_e, next) => {
      if (!next || !onAgentModeChange) return;
      onAgentModeChange(next);
    },
    [onAgentModeChange],
  );

  const toggleWebResearch = useCallback(() => {
    if (!onWebResearchEnabledChange || loading || structuredAnswerPending) return;
    onWebResearchEnabledChange(!webResearchEnabled);
  }, [loading, onWebResearchEnabledChange, structuredAnswerPending, webResearchEnabled]);

  const composerShellSx = useMemo(
    () => ({
      borderRadius: "6px",
      border: `1px solid ${tk.border.strong}`,
      backgroundColor: tk.surface.panel,
      p: 1.1,
      display: "flex",
      flexDirection: "column",
      gap: 0.75,
      transition: "border-color 0.15s ease, background-color 0.15s ease",
      "&:focus-within": {
        borderColor: tk.accent.softBorder,
        backgroundColor: tk.surface.panelAlt,
      },
      "&:focus-within .composer-enter-hint": {
        color: `${tk.text.secondary}`,
      },
    }),
    [tk],
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
      <Box sx={composerShellSx}>
        {locked ? (
          <Box sx={{ px: 0.5, pt: 0.25, display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
            <Typography sx={{ fontSize: "0.68rem", color: tk.text.muted }}>{t("askPanel.workIdScopeLabel")}</Typography>
            <Typography sx={{ fontSize: "0.75rem", color: tk.text.primary, fontFamily: "monospace" }}>{String(scopedWorkId || workId).trim()}</Typography>
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
          <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, px: 0.5 }}>{streamingHint}</Typography>
        ) : null}
        {structuredAnswerPending ? (
          <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, px: 0.5 }}>{t("askPanel.userQuestion.composerBlocked")}</Typography>
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
          disabled={structuredAnswerPending}
          sx={{ ...inputSx, px: 0.5 }}
        />
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, flexWrap: "wrap", px: 0.25 }}>
          <ToggleButtonGroup
            exclusive
            size="small"
            value={agentMode}
            onChange={handleAgentModeChange}
            disabled={loading || structuredAnswerPending}
            aria-label={t("chat.composer.agentModeGroupAria")}
            sx={{
              "& .MuiToggleButton-root": {
                fontSize: "0.75rem",
                py: 0.25,
                px: 0.85,
                textTransform: "none",
                borderRadius: "6px",
                color: tk.text.muted,
                border: `1px solid ${tk.border.default}`,
              },
              "& .MuiToggleButtonGroup-grouped": { borderRadius: "6px !important" },
              "& .Mui-selected": {
                color: `${tk.accent.fg} !important`,
                backgroundColor: `${tk.accent.emphasisHoverBg} !important`,
                borderColor: `${tk.accent.emphasisHoverBorder} !important`,
              },
            }}
          >
            <ToggleButton value="agent">{t("chat.composer.modeAgent")}</ToggleButton>
            <ToggleButton value="plan">{t("chat.composer.modePlan")}</ToggleButton>
          </ToggleButtonGroup>
        </Box>
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
          <Typography
            className="composer-enter-hint"
            sx={{
              fontSize: "0.68rem",
              color: tk.text.muted,
              flex: "1 1 auto",
              minWidth: 0,
              transition: "color 0.15s ease",
            }}
          >
            {t("chat.composer.enterHint")}
          </Typography>
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
                  color: tk.text.muted,
                  border: `1px solid ${tk.border.default}`,
                  borderRadius: "6px",
                  "&:hover": { backgroundColor: tk.control.navItemHoverBg },
                }}
              >
                <OpenInNewOutlinedIcon sx={{ fontSize: "1rem" }} />
              </IconButton>
            ) : null}
            {onClearChatClick ? (
              <IconButton
                type="button"
                onClick={onClearChatClick}
                disabled={clearChatDisabled}
                aria-label={t("chat.composer.clearChatAria")}
                title={t("chat.composer.clearChatTitle")}
                size="small"
                sx={{
                  color: tk.text.muted,
                  border: `1px solid ${tk.border.default}`,
                  borderRadius: "6px",
                  "&:hover": { backgroundColor: tk.control.navItemHoverBg },
                }}
              >
                <DeleteSweepOutlinedIcon sx={{ fontSize: "1rem" }} />
              </IconButton>
            ) : null}
            <IconButton
              type="button"
              onClick={toggleWebResearch}
              disabled={loading || structuredAnswerPending}
              aria-label={
                webResearchEnabled
                  ? t("chat.composer.webResearchOnAria")
                  : t("chat.composer.webResearchOffAria")
              }
              title={t("chat.composer.webResearchTitle")}
              size="small"
              sx={{
                color: webResearchEnabled ? tk.accent.fg : tk.text.muted,
                border: `1px solid ${webResearchEnabled ? tk.accent.emphasisHoverBorder : tk.border.default}`,
                borderRadius: "6px",
                backgroundColor: webResearchEnabled ? tk.accent.emphasisHoverBg : "transparent",
                "&:hover": { backgroundColor: tk.control.navItemHoverBg },
              }}
            >
              <PublicOutlinedIcon sx={{ fontSize: "1.05rem" }} />
            </IconButton>
            <IconButton
              type="submit"
              size="small"
              disabled={loading || structuredAnswerPending || !String(query || "").trim()}
              aria-label={loading ? t("chat.composer.sending") : t("chat.composer.sendAria")}
              title={loading ? t("chat.composer.sending") : t("chat.composer.sendAria")}
              sx={{
                color: tk.accent.fg,
                backgroundColor: tk.accent.emphasisHoverBg,
                border: `1px solid ${tk.accent.emphasisHoverBorder}`,
                "&:hover": { backgroundColor: tk.accent.emphasisHoverBg },
                "&.Mui-disabled": { color: tk.text.faint, borderColor: tk.border.default },
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
