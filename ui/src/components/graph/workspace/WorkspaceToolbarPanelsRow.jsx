import React from "react";
import BusinessOutlinedIcon from "@mui/icons-material/BusinessOutlined";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import GraphViewChips from "../toolbar/GraphViewChips.jsx";

/**
 * View chips, institutions toggle, and workspace stats (second toolbar zone).
 *
 * @param {{
 *   viewChipsProps: object,
 *   ctxWork: string,
 *   onToggleWorkGraphIncludeInstitutions?: () => void,
 *   workGraphIncludeInstitutions: boolean,
 *   institutionChipSx: (active: boolean) => object,
 *   dividerSx: object,
 *   statsFragments: Array<{ key: string, text: string, tip: string }>,
 *   statsTypographySx: object,
 *   t: (k: string, opts?: object) => string,
 * }} props
 */
export default function WorkspaceToolbarPanelsRow({
  viewChipsProps,
  ctxWork,
  onToggleWorkGraphIncludeInstitutions,
  workGraphIncludeInstitutions,
  institutionChipSx,
  dividerSx,
  statsFragments,
  statsTypographySx,
  t,
}) {
  const statsBlock =
    statsFragments.length > 0 ? (
      <Typography component="span" sx={statsTypographySx}>
        {statsFragments.map((frag, i) => (
          <React.Fragment key={frag.key}>
            {i > 0 ? " · " : null}
            <Tooltip title={frag.tip}>
              <Box component="span" sx={{ cursor: "default" }}>
                {frag.text}
              </Box>
            </Tooltip>
          </React.Fragment>
        ))}
      </Typography>
    ) : null;

  const institutionsBlock =
    ctxWork && onToggleWorkGraphIncludeInstitutions ? (
      <>
        <Divider orientation="vertical" flexItem sx={dividerSx} />
        <Tooltip title={t("graph.wsToolbar.chipInstitutionsTooltip")}>
          <Chip
            size="small"
            variant="outlined"
            icon={<BusinessOutlinedIcon sx={{ fontSize: "1rem !important" }} />}
            label={t("graph.wsToolbar.chipInstitutions")}
            onClick={onToggleWorkGraphIncludeInstitutions}
            aria-pressed={workGraphIncludeInstitutions}
            aria-label={t("graph.wsToolbar.chipInstitutionsAria")}
            sx={institutionChipSx(workGraphIncludeInstitutions)}
          />
        </Tooltip>
      </>
    ) : null;

  return (
    <>
      <GraphViewChips {...viewChipsProps} />
      {institutionsBlock}
      {statsBlock}
    </>
  );
}
