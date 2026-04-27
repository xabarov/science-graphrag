import React, { useCallback, useState } from "react";
import ExpandMoreOutlinedIcon from "@mui/icons-material/ExpandMoreOutlined";
import FilterListOutlinedIcon from "@mui/icons-material/FilterListOutlined";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Popover from "@mui/material/Popover";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorButton } from "../../common/index.js";
import { getScienceGraphNodeTypeIcon } from "../graphCanvasStyle.js";

const NODE_TYPE_OPTIONS = /** @type {const} */ (["Work", "Author", "Method", "Dataset", "Venue", "Institution"]);

/**
 * @param {{
 *   selectedSet: Set<string>,
 *   onToggleType: (nodeType: string) => void,
 *   t: (key: string, vars?: Record<string, string>) => string,
 * }} props
 */
export default function GraphNodeTypesMenu({ selectedSet, onToggleType, t }) {
  const tk = useTheme().appTokens;
  const [anchor, setAnchor] = useState(null);
  const open = Boolean(anchor);
  const total = NODE_TYPE_OPTIONS.length;
  const selected = NODE_TYPE_OPTIONS.filter((x) => selectedSet.has(x)).length;
  const summary = t("graph.wsToolbar.nodeTypesSummary", { selected: String(selected), total: String(total) });

  const handleClose = useCallback(() => setAnchor(null), []);

  return (
    <>
      <Tooltip title={t("graph.wsToolbar.nodeTypesButtonTooltip")} placement="bottom">
        <Box component="span">
          <CursorButton
            type="button"
            size="small"
            onClick={(e) => setAnchor(e.currentTarget)}
            aria-haspopup="true"
            aria-expanded={open ? "true" : undefined}
            aria-controls={open ? "graph-node-types-popover" : undefined}
            startIcon={<FilterListOutlinedIcon sx={{ fontSize: "1rem !important" }} />}
            endIcon={<ExpandMoreOutlinedIcon sx={{ fontSize: "1rem !important", opacity: 0.75 }} />}
            sx={{
              fontSize: "0.75rem",
              py: 0.35,
              px: 0.75,
              textTransform: "none",
              borderColor: tk.border.strong,
              color: tk.text.primary,
              minWidth: 0,
            }}
          >
            {summary}
          </CursorButton>
        </Box>
      </Tooltip>
      <Popover
        id="graph-node-types-popover"
        open={open}
        anchorEl={anchor}
        onClose={handleClose}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
        transformOrigin={{ vertical: "top", horizontal: "left" }}
        slotProps={{
          paper: {
            sx: {
              mt: 0.5,
              p: 1.25,
              minWidth: 280,
              maxWidth: 360,
              backgroundColor: tk.surface.panel,
              border: `1px solid ${tk.border.default}`,
            },
          },
        }}
      >
        <Typography sx={{ fontSize: "0.75rem", fontWeight: 600, color: tk.text.muted, mb: 1 }}>
          {t("graph.wsToolbar.nodeTypesPopoverTitle")}
        </Typography>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.25 }}>
          {NODE_TYPE_OPTIONS.map((nodeType) => {
            const TypeIcon = getScienceGraphNodeTypeIcon(nodeType);
            const checked = selectedSet.has(nodeType);
            return (
              <FormControlLabel
                key={nodeType}
                control={
                  <Checkbox
                    size="small"
                    checked={checked}
                    onChange={() => onToggleType(nodeType)}
                    sx={{ py: 0.25, color: tk.text.muted, "&.Mui-checked": { color: tk.accent.fg } }}
                  />
                }
                label={
                  <Box sx={{ display: "flex", alignItems: "flex-start", gap: 0.75, minWidth: 0 }}>
                    {TypeIcon ? <TypeIcon sx={{ fontSize: "1.05rem", color: tk.text.secondary, mt: 0.15 }} /> : null}
                    <Box sx={{ minWidth: 0 }}>
                      <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, lineHeight: 1.2 }}>
                        {t(`graph.wsToolbar.nodeType.${nodeType}`)}
                      </Typography>
                      <Typography sx={{ fontSize: "0.68rem", color: tk.text.faint, mt: 0.2, lineHeight: 1.3 }}>
                        {t(`graph.wsToolbar.nodeTypeDesc.${nodeType}`)}
                      </Typography>
                    </Box>
                  </Box>
                }
                sx={{ m: 0, alignItems: "flex-start", "& .MuiFormControlLabel-label": { flex: 1, minWidth: 0 } }}
              />
            );
          })}
        </Box>
      </Popover>
    </>
  );
}
