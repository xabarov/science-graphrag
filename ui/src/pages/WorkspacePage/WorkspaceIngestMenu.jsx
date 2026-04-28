import React, { useCallback, useState } from "react";
import Popover from "@mui/material/Popover";
import Tooltip from "@mui/material/Tooltip";
import { useTheme } from "@mui/material/styles";

import AddOutlinedIcon from "@mui/icons-material/AddOutlined";

import { CursorIconButton } from "../../components/common/index.js";

import WorkspaceIngestPanel from "./WorkspaceIngestPanel.jsx";

/**
 * Compact "Add" trigger opening ingest + advanced add-by-id in a popover.
 * @param {{
 *   workspaceId: string,
 *   uploadBusy: boolean,
 *   ingestJobId: string,
 *   ingestJob: object | null,
 *   ingestErr: string | null,
 *   onUploadDocument: (ev: React.ChangeEvent<HTMLInputElement>) => void,
 *   onUploadBatch?: (files: File[], archive: File | null) => void | Promise<void>,
 *   addWorkInput: string,
 *   onAddWorkInputChange: (v: string) => void,
 *   addBusy: boolean,
 *   onAddWork: (e?: React.FormEvent) => void | Promise<void>,
 *   menuButtonAria: string,
 *   menuButtonTooltip: string,
 * }} props
 */
export default function WorkspaceIngestMenu({
  workspaceId,
  uploadBusy,
  ingestJobId,
  ingestJob,
  ingestErr,
  onUploadDocument,
  onUploadBatch,
  addWorkInput,
  onAddWorkInputChange,
  addBusy,
  onAddWork,
  menuButtonAria,
  menuButtonTooltip,
}) {
  const theme = useTheme();
  const tk = theme.appTokens;
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);

  const handleClose = useCallback(() => {
    setAnchorEl(null);
  }, []);

  if (!workspaceId) return null;

  return (
    <>
      <Tooltip title={menuButtonTooltip}>
        <span>
          <CursorIconButton
            type="button"
            aria-label={menuButtonAria}
            aria-haspopup="true"
            aria-expanded={open}
            onClick={(e) => setAnchorEl(e.currentTarget)}
            sx={{
              border: `1px solid ${tk.accent.softBorder}`,
              backgroundColor: tk.accent.chipReadyBg,
              "&:hover": { backgroundColor: tk.accent.emphasisHoverBg },
            }}
          >
            <AddOutlinedIcon sx={{ fontSize: "1.1rem" }} />
          </CursorIconButton>
        </span>
      </Tooltip>
      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        slotProps={{
          paper: {
            sx: {
              mt: 0.75,
              minWidth: 300,
              maxWidth: 420,
              maxHeight: "min(85dvh, 640px)",
              overflow: "auto",
              p: 1.25,
              backgroundColor: tk.surface.panel,
              border: `1px solid ${tk.border.default}`,
              borderRadius: "6px",
            },
          },
        }}
      >
        <WorkspaceIngestPanel
          workspaceId={workspaceId}
          uploadBusy={uploadBusy}
          ingestJobId={ingestJobId}
          ingestJob={ingestJob}
          ingestErr={ingestErr}
          onUploadDocument={onUploadDocument}
          onUploadBatch={onUploadBatch}
          addWorkInput={addWorkInput}
          onAddWorkInputChange={onAddWorkInputChange}
          addBusy={addBusy}
          onAddWork={onAddWork}
          variant="popover"
        />
      </Popover>
    </>
  );
}
