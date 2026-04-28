import React from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Typography from "@mui/material/Typography";

import { CursorPrimaryButton } from "../../components/common/index.js";
import HypothesisPanel from "../../components/work/hypothesis/HypothesisPanel.jsx";

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   summaryOpen: boolean,
 *   onSummaryClose: () => void,
 *   summaryText: string,
 *   ideaOpen: boolean,
 *   onIdeaClose: () => void,
 *   ideaResult: { hypotheses: unknown[], contradictions: unknown[], toolTrace: unknown[] },
 *   ideaBusy: boolean,
 *   ideaError: string,
 * }} props
 */
export default function WorkspaceDialogs({
  t,
  summaryOpen,
  onSummaryClose,
  summaryText,
  ideaOpen,
  onIdeaClose,
  ideaResult,
  ideaBusy,
  ideaError,
}) {
  return (
    <>
      <Dialog open={summaryOpen} onClose={onSummaryClose} maxWidth="md" fullWidth>
        <DialogTitle>{t("workspace.summary.dialogTitle")}</DialogTitle>
        <DialogContent>
          <Typography sx={{ whiteSpace: "pre-wrap", fontSize: "0.875rem" }}>
            {summaryText || t("workspace.summary.empty")}
          </Typography>
        </DialogContent>
        <DialogActions>
          <CursorPrimaryButton onClick={onSummaryClose}>{t("workspace.dialog.close")}</CursorPrimaryButton>
        </DialogActions>
      </Dialog>
      <Dialog open={ideaOpen} onClose={onIdeaClose} maxWidth="md" fullWidth>
        <DialogTitle>{t("workspace.idea.dialogTitle")}</DialogTitle>
        <DialogContent>
          <HypothesisPanel
            hypotheses={ideaResult.hypotheses}
            contradictions={ideaResult.contradictions}
            toolTrace={ideaResult.toolTrace}
            loading={ideaBusy}
            error={ideaError}
          />
        </DialogContent>
        <DialogActions>
          <CursorPrimaryButton onClick={onIdeaClose}>{t("workspace.dialog.close")}</CursorPrimaryButton>
        </DialogActions>
      </Dialog>
    </>
  );
}
