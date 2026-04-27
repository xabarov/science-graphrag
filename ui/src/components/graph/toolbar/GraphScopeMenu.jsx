import React, { useCallback, useState } from "react";
import AllInclusiveOutlinedIcon from "@mui/icons-material/AllInclusiveOutlined";
import BiotechOutlinedIcon from "@mui/icons-material/BiotechOutlined";
import ExpandMoreOutlinedIcon from "@mui/icons-material/ExpandMoreOutlined";
import HomeOutlinedIcon from "@mui/icons-material/HomeOutlined";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";
import Box from "@mui/material/Box";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorButton } from "../../common/index.js";

const MODE_ORDER = /** @type {const} */ (["inner_only", "union_1hop", "semantic_layer", "full"]);

const MODE_ICONS = {
  inner_only: HomeOutlinedIcon,
  union_1hop: HubOutlinedIcon,
  semantic_layer: BiotechOutlinedIcon,
  full: AllInclusiveOutlinedIcon,
};

/**
 * @param {{
 *   value: string,
 *   onChange: (mode: string) => void,
 *   t: (key: string, vars?: Record<string, string>) => string,
 * }} props
 */
export default function GraphScopeMenu({ value, onChange, t }) {
  const tk = useTheme().appTokens;
  const [anchor, setAnchor] = useState(null);
  const open = Boolean(anchor);

  const handleClose = useCallback(() => setAnchor(null), []);

  const modeLabel = useCallback(
    (mode) => {
      const key = `graph.wsToolbar.mode${mode === "inner_only" ? "Inner" : mode === "union_1hop" ? "Union1hop" : mode === "semantic_layer" ? "Semantic" : "Full"}`;
      return t(key);
    },
    [t],
  );

  const triggerLabel = `${t("graph.wsToolbar.scope")}: ${modeLabel(value)}`;

  return (
    <>
      <Tooltip title={t("graph.wsToolbar.scopeTriggerTooltip")} placement="bottom">
        <Box component="span">
          <CursorButton
            type="button"
            size="small"
            onClick={(e) => setAnchor(e.currentTarget)}
            aria-haspopup="true"
            aria-expanded={open ? "true" : undefined}
            aria-controls={open ? "graph-scope-menu" : undefined}
            aria-label={t("graph.wsToolbar.scopeMenuAria")}
            sx={{
              fontSize: "0.75rem",
              py: 0.35,
              px: 0.85,
              textTransform: "none",
              borderColor: tk.border.strong,
              color: tk.text.primary,
              minWidth: 0,
              maxWidth: { xs: "100%", sm: 280 },
            }}
            endIcon={<ExpandMoreOutlinedIcon sx={{ fontSize: "1rem !important", opacity: 0.75 }} />}
          >
            {triggerLabel}
          </CursorButton>
        </Box>
      </Tooltip>
      <Menu
        id="graph-scope-menu"
        anchorEl={anchor}
        open={open}
        onClose={handleClose}
        slotProps={{
          paper: {
            sx: {
              minWidth: 260,
              maxWidth: 340,
              backgroundColor: tk.surface.panel,
              border: `1px solid ${tk.border.default}`,
            },
          },
        }}
      >
        {MODE_ORDER.map((mode) => {
          const Icon = MODE_ICONS[mode];
          const selected = value === mode;
          return (
            <MenuItem
              key={mode}
              selected={selected}
              onClick={() => {
                onChange(mode);
                handleClose();
              }}
              dense
              sx={{ py: 1, alignItems: "flex-start" }}
            >
              <ListItemIcon sx={{ minWidth: 36, mt: 0.25 }}>
                <Icon sx={{ fontSize: "1.15rem", color: tk.text.secondary }} />
              </ListItemIcon>
              <ListItemText
                primary={
                  <Typography sx={{ fontSize: "0.8125rem", fontWeight: 600, color: tk.text.primary }}>
                    {modeLabel(mode)}
                  </Typography>
                }
                secondary={
                  <Typography sx={{ fontSize: "0.7rem", color: tk.text.muted, mt: 0.25, lineHeight: 1.35 }}>
                    {t(`graph.wsToolbar.scopeDesc.${mode}`)}
                  </Typography>
                }
              />
            </MenuItem>
          );
        })}
      </Menu>
    </>
  );
}
