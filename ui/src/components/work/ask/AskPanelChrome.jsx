import React from "react";
import DeleteSweepOutlinedIcon from "@mui/icons-material/DeleteSweepOutlined";
import TuneOutlinedIcon from "@mui/icons-material/TuneOutlined";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { InlineNotice } from "../../feedback/index.js";
import { CursorSmallButton } from "../../common/index.js";

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   tk: Record<string, unknown>,
 *   detailLevel: "simple" | "detailed",
 *   onToggleDetailLevel?: () => void,
 *   iconButtonSx?: object,
 * }} props
 */
function ChatDetailLevelToggle({ t, tk, detailLevel, onToggleDetailLevel, iconButtonSx = {} }) {
  if (!onToggleDetailLevel) return null;
  return (
    <IconButton
      type="button"
      size="small"
      onClick={onToggleDetailLevel}
      aria-label={t("chat.chrome.detailToggleAria")}
      aria-pressed={detailLevel === "detailed"}
      title={detailLevel === "detailed" ? t("chat.chrome.detailModeDetailed") : t("chat.chrome.detailModeSimple")}
      sx={{
        flexShrink: 0,
        color: tk.text.muted,
        border: `1px solid ${tk.border.default}`,
        borderRadius: "6px",
        "&:hover": { backgroundColor: tk.control.navItemHoverBg },
        ...iconButtonSx,
      }}
    >
      <TuneOutlinedIcon sx={{ fontSize: "1rem" }} />
    </IconButton>
  );
}

/**
 * Page chrome (title/body) or compact chat eyebrow + submit/stream errors.
 *
 * @param {{
 *   showPageChrome: boolean,
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   scopeEyebrow: string,
 *   error: string | null,
 *   onClearChatClick?: () => void,
 *   clearChatDisabled?: boolean,
 *   detailLevel?: "simple" | "detailed",
 *   onToggleDetailLevel?: () => void,
 * }} props
 */
export function AskPanelChrome({
  showPageChrome,
  t,
  scopeEyebrow,
  error,
  onClearChatClick,
  clearChatDisabled = false,
  detailLevel = "simple",
  onToggleDetailLevel,
}) {
  const tk = useTheme().appTokens;
  return (
    <>
      {showPageChrome ? (
        <Box
          sx={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 1,
            mb: 1,
          }}
        >
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography sx={{ fontWeight: 600, mb: 0.5, color: tk.text.primary }}>{t("askPanel.chromeTitle")}</Typography>
            <Typography sx={{ color: tk.text.secondary, fontSize: "0.8125rem" }}>{t("askPanel.chromeBody")}</Typography>
          </Box>
          <ChatDetailLevelToggle
            t={t}
            tk={tk}
            detailLevel={detailLevel}
            onToggleDetailLevel={onToggleDetailLevel}
            iconButtonSx={{ mt: -0.25 }}
          />
        </Box>
      ) : (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5, flexShrink: 0, minWidth: 0 }}>
          <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, flex: 1, minWidth: 0 }} noWrap title={scopeEyebrow}>
            {scopeEyebrow}
          </Typography>
          <ChatDetailLevelToggle t={t} tk={tk} detailLevel={detailLevel} onToggleDetailLevel={onToggleDetailLevel} />
          {onClearChatClick ? (
            <CursorSmallButton
              type="button"
              disabled={clearChatDisabled}
              aria-label={t("chat.clear.openAria")}
              title={t("chat.clear.openAria")}
              startIcon={<DeleteSweepOutlinedIcon sx={{ fontSize: "1rem !important" }} />}
              onClick={onClearChatClick}
              sx={{ flexShrink: 0, py: 0.25, minHeight: 28 }}
            >
              {t("chat.clear.button")}
            </CursorSmallButton>
          ) : null}
        </Box>
      )}
      {error ? (
        <InlineNotice severity="error" sx={{ flexShrink: 0 }}>
          {error}
        </InlineNotice>
      ) : null}
    </>
  );
}
