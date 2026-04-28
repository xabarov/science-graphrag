import React from "react";
import DeleteSweepOutlinedIcon from "@mui/icons-material/DeleteSweepOutlined";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { InlineNotice } from "../feedback/index.js";
import { CursorSmallButton } from "../common/index.js";

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
 * }} props
 */
export function AskPanelChrome({ showPageChrome, t, scopeEyebrow, error, onClearChatClick, clearChatDisabled = false }) {
  const tk = useTheme().appTokens;
  return (
    <>
      {showPageChrome ? (
        <>
          <Typography sx={{ fontWeight: 600, mb: 0.5, color: tk.text.primary }}>{t("askPanel.chromeTitle")}</Typography>
          <Typography sx={{ color: tk.text.secondary, fontSize: "0.8125rem", mb: 1 }}>{t("askPanel.chromeBody")}</Typography>
        </>
      ) : (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5, flexShrink: 0, minWidth: 0 }}>
          <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, flex: 1, minWidth: 0 }} noWrap title={scopeEyebrow}>
            {scopeEyebrow}
          </Typography>
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
