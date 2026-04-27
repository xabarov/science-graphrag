import React from "react";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import { useTheme } from "@mui/material/styles";

import { feedbackDialogPaperSx } from "./dialogPaperSx.js";

/**
 * Reusable dialog shell (title + body + actions).
 *
 * @param {{
 *   open: boolean,
 *   onClose: (event: object, reason: string) => void,
 *   title: React.ReactNode,
 *   titleId?: string,
 *   children: React.ReactNode,
 *   actions: React.ReactNode,
 *   "aria-labelledby"?: string,
 *   "aria-describedby"?: string,
 * }} props
 */
export function FeedbackShell({
  open,
  onClose,
  title,
  titleId = "feedback-dialog-title",
  children,
  actions,
  "aria-labelledby": ariaLabelledBy,
  "aria-describedby": ariaDescribedBy,
}) {
  const theme = useTheme();
  const tk = theme.appTokens;
  const labelledBy = ariaLabelledBy || titleId;
  return (
    <Dialog
      open={open}
      onClose={onClose}
      aria-labelledby={labelledBy}
      aria-describedby={ariaDescribedBy}
      slotProps={{
        paper: {
          sx: feedbackDialogPaperSx(theme),
        },
      }}
    >
      <DialogTitle id={titleId} sx={{ fontSize: "0.9375rem", fontWeight: 600, color: tk.text.primary }}>
        {title}
      </DialogTitle>
      <DialogContent {...(ariaDescribedBy ? { id: ariaDescribedBy } : {})} sx={{ color: tk.text.secondary, fontSize: "0.8125rem" }}>
        {children}
      </DialogContent>
      <DialogActions sx={{ px: 2, pb: 1.5, gap: 1 }}>{actions}</DialogActions>
    </Dialog>
  );
}
