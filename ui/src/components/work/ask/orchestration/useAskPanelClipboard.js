import { useCallback } from "react";

import { useI18n } from "../../../../i18n/useI18n.js";
import { copyToClipboard } from "../../../../utils/copyToClipboard.js";
import { useFeedback } from "../../../feedback/index.js";

/** Clipboard + toast helpers for Ask panel chrome. */
export function useAskPanelClipboard() {
  const { t } = useI18n();
  const { showToast } = useFeedback();

  const onCopyUserText = useCallback(
    async (text) => {
      const ok = await copyToClipboard(String(text || ""));
      showToast(t(ok ? "chat.copy.success" : "chat.copy.failed"));
    },
    [showToast, t],
  );

  const onCopyAssistantEntry = useCallback(
    async (entry) => {
      let plain = "";
      if (entry?.details && typeof entry.details === "object") {
        plain = String(entry.details.answer ?? "");
      } else {
        plain = String(entry?.answer ?? "");
      }
      const ok = await copyToClipboard(plain);
      showToast(t(ok ? "chat.copy.success" : "chat.copy.failed"));
    },
    [showToast, t],
  );

  return { onCopyUserText, onCopyAssistantEntry };
}
