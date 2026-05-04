import React from "react";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import CropFreeIcon from "@mui/icons-material/CropFree";
import MyLocationIcon from "@mui/icons-material/MyLocation";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";

/**
 * @param {{
 *   open: boolean,
 *   anchor: { mouseX: number, mouseY: number, nodeId: string } | null,
 *   onClose: () => void,
 *   onFit: (nodeId: string) => void,
 *   onCenter: (nodeId: string) => void,
 *   onSelectNode: (nodeId: string) => void,
 *   labels: { fit: string, center: string, copyId: string },
 * }} props
 */
export default function GraphCanvasNodeContextMenu({ open, anchor, onClose, onFit, onCenter, onSelectNode, labels }) {
  return (
    <Menu open={open} onClose={onClose} anchorReference="anchorPosition" anchorPosition={anchor ? { top: anchor.mouseY, left: anchor.mouseX } : undefined}>
      <MenuItem
        onClick={() => {
          const nid = anchor?.nodeId;
          onClose();
          if (!nid) return;
          onSelectNode(nid);
          onFit(nid);
        }}
      >
        <CropFreeIcon fontSize="small" sx={{ mr: 1 }} />
        {labels.fit}
      </MenuItem>
      <MenuItem
        onClick={() => {
          const nid = anchor?.nodeId;
          onClose();
          if (!nid) return;
          onCenter(nid);
        }}
      >
        <MyLocationIcon fontSize="small" sx={{ mr: 1 }} />
        {labels.center}
      </MenuItem>
      <MenuItem
        onClick={() => {
          const nid = anchor?.nodeId;
          onClose();
          if (!nid) return;
          try {
            void navigator.clipboard?.writeText?.(nid);
          } catch {
            /* ignore */
          }
        }}
      >
        <ContentCopyIcon fontSize="small" sx={{ mr: 1 }} />
        {labels.copyId}
      </MenuItem>
    </Menu>
  );
}
