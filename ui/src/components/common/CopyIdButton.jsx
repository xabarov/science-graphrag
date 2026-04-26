import React, { useCallback, useState } from "react";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";

import { copyToClipboard } from "../../utils/copyToClipboard.js";
import CursorIconAction from "./CursorIconAction.jsx";

/**
 * Small icon to copy an id without showing the id in the layout.
 *
 * @param {{ id: string, tooltipCopy: string, tooltipCopied: string, "aria-label"?: string }} props
 */
export default function CopyIdButton({ id, tooltipCopy, tooltipCopied, "aria-label": ariaLabel }) {
  const [copied, setCopied] = useState(false);

  const handleClick = useCallback(
    async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const ok = await copyToClipboard(id);
      if (!ok) return;
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    },
    [id],
  );

  if (!id) return null;

  return (
    <CursorIconAction
      title={copied ? tooltipCopied : tooltipCopy}
      onClick={handleClick}
      aria-label={ariaLabel || tooltipCopy}
    >
      <ContentCopyIcon sx={{ fontSize: "1rem" }} />
    </CursorIconAction>
  );
}
