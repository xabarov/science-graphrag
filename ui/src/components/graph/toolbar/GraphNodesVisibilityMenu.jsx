import React, { useCallback, useMemo, useState } from "react";
import ExpandMoreOutlinedIcon from "@mui/icons-material/ExpandMoreOutlined";
import FilterListOutlinedIcon from "@mui/icons-material/FilterListOutlined";
import PublicOutlinedIcon from "@mui/icons-material/PublicOutlined";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Popover from "@mui/material/Popover";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorButton } from "../../common/index.js";
import { getScienceGraphNodeTypeIcon } from "../canvas/graphCanvasStyle.js";
import { GRAPH_VISIBILITY_DOMAIN_TYPES } from "../model/graphVisibilityFilter.js";

const MENU_TYPE_TOTAL = GRAPH_VISIBILITY_DOMAIN_TYPES.length + 1;

/** @type {Record<string, import("react").ComponentType<{ sx?: object }> | null>} */
const DOMAIN_TYPE_ICONS = Object.fromEntries(
  GRAPH_VISIBILITY_DOMAIN_TYPES.map((k) => [k, getScienceGraphNodeTypeIcon(k)]),
);

/**
 * @param {{
 *   visibility: import("../model/graphVisibilityFilter.js").GraphVisibilityValue,
 *   onChange: (patch: Partial<import("../model/graphVisibilityFilter.js").GraphVisibilityValue>) => void,
 *   t: (key: string, vars?: Record<string, string>) => string,
 * }} props
 */
export default function GraphNodesVisibilityMenu({ visibility, onChange, t }) {
  const tk = useTheme().appTokens;
  const [anchor, setAnchor] = useState(null);
  const open = Boolean(anchor);
  const typeSet = useMemo(() => new Set(Array.isArray(visibility?.types) ? visibility.types : []), [visibility]);

  const handleClose = useCallback(() => setAnchor(null), []);

  const toggleType = useCallback(
    (typeKey) => {
      const next = new Set(typeSet);
      if (next.has(typeKey)) {
        if (next.size <= 1) return;
        next.delete(typeKey);
      } else {
        next.add(typeKey);
      }
      onChange({ types: [...next] });
    },
    [onChange, typeSet],
  );

  const toggleExternalWorks = useCallback(() => {
    onChange({ showExternalWorks: !visibility?.showExternalWorks });
  }, [onChange, visibility?.showExternalWorks]);

  const typesOnCount = useMemo(() => {
    const domainOn = GRAPH_VISIBILITY_DOMAIN_TYPES.filter((k) => typeSet.has(k)).length;
    const extOn = visibility?.showExternalWorks ? 1 : 0;
    return domainOn + extOn;
  }, [typeSet, visibility?.showExternalWorks]);

  const activeTypeTags = useMemo(() => {
    const parts = [];
    for (const k of GRAPH_VISIBILITY_DOMAIN_TYPES) {
      if (typeSet.has(k)) parts.push(t(`graph.wsToolbar.nodeTypeTag.${k}`));
    }
    if (visibility?.showExternalWorks) parts.push(t("graph.wsToolbar.nodesExtraExtShort"));
    return parts;
  }, [t, typeSet, visibility?.showExternalWorks]);

  const extras =
    activeTypeTags.length > 0
      ? ` · ${activeTypeTags.slice(0, 5).join(" · ")}${activeTypeTags.length > 5 ? "…" : ""}`
      : "";

  const summary = t("graph.wsToolbar.nodesMenuButtonLabel", {
    typesOn: String(typesOnCount),
    typesTotal: String(MENU_TYPE_TOTAL),
    extras,
  });

  return (
    <>
      <Tooltip title={t("graph.wsToolbar.nodesMenuButtonTooltip")} placement="bottom">
        <Box component="span">
          <CursorButton
            type="button"
            size="small"
            onClick={(e) => setAnchor(e.currentTarget)}
            aria-haspopup="true"
            aria-expanded={open ? "true" : undefined}
            aria-controls={open ? "graph-nodes-visibility-popover" : undefined}
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
        id="graph-nodes-visibility-popover"
        open={open}
        anchorEl={anchor}
        onClose={handleClose}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        slotProps={{
          paper: {
            sx: {
              mt: 0.5,
              p: 1.25,
              minWidth: 300,
              maxWidth: 400,
              maxHeight: "min(70vh, 520px)",
              overflow: "auto",
              backgroundColor: tk.surface.panel,
              border: `1px solid ${tk.border.default}`,
            },
          },
        }}
      >
        <Typography sx={{ fontSize: "0.75rem", fontWeight: 600, color: tk.text.muted, mb: 1 }}>
          {t("graph.wsToolbar.nodesMenuPopoverTitle")}
        </Typography>
        <Typography sx={{ fontSize: "0.68rem", color: tk.text.faint, mb: 1.25, lineHeight: 1.35 }}>
          {t("graph.wsToolbar.nodesMenuPopoverHint")}
        </Typography>

        <Typography sx={{ fontSize: "0.72rem", fontWeight: 600, color: tk.text.secondary, mb: 0.75 }}>
          {t("graph.wsToolbar.nodesSectionTypes")}
        </Typography>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.25, pb: 0.5 }}>
          {GRAPH_VISIBILITY_DOMAIN_TYPES.map((nodeType) => {
            const TypeIcon = DOMAIN_TYPE_ICONS[nodeType];
            const checked = typeSet.has(nodeType);
            return (
              <FormControlLabel
                key={nodeType}
                control={
                  <Checkbox
                    size="small"
                    checked={checked}
                    onChange={() => toggleType(nodeType)}
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
          <FormControlLabel
            control={
              <Checkbox
                size="small"
                checked={Boolean(visibility?.showExternalWorks)}
                onChange={toggleExternalWorks}
                sx={{ py: 0.25, color: tk.text.muted, "&.Mui-checked": { color: tk.accent.fg } }}
              />
            }
            label={
              <Box sx={{ display: "flex", alignItems: "flex-start", gap: 0.75, minWidth: 0 }}>
                <PublicOutlinedIcon sx={{ fontSize: "1.05rem", color: tk.text.secondary, mt: 0.15 }} />
                <Box sx={{ minWidth: 0 }}>
                  <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, lineHeight: 1.2 }}>
                    {t("graph.wsToolbar.extensionExternalCites")}
                  </Typography>
                  <Typography sx={{ fontSize: "0.68rem", color: tk.text.faint, mt: 0.2, lineHeight: 1.3 }}>
                    {t("graph.wsToolbar.extensionExternalCitesDesc")}
                  </Typography>
                </Box>
              </Box>
            }
            sx={{ m: 0, alignItems: "flex-start", "& .MuiFormControlLabel-label": { flex: 1, minWidth: 0 } }}
          />
        </Box>
      </Popover>
    </>
  );
}
