import React from "react";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import { graphDetailClaimBodySx, graphDetailCodePreSx } from "../graphNodeDetailSectionSx.js";

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   t: (k: string, opts?: object) => string,
 *   claimBody: string,
 *   claimMetadataFormatted: string,
 *   compact: boolean,
 * }} props
 */
export default function GraphClaimSection({ tk, t, claimBody, claimMetadataFormatted, compact }) {
  if (!claimBody && !claimMetadataFormatted) return null;
  return (
    <>
      {claimBody ? (
        <Box sx={{ mt: 2, mb: 1 }}>
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 0.5, color: tk.text.primary }}>
            {t("graph.detailPanel.claimBody")}
          </Typography>
          <Typography component="div" sx={graphDetailClaimBodySx(tk, compact)}>
            {claimBody}
          </Typography>
        </Box>
      ) : null}
      {claimMetadataFormatted ? (
        <Accordion
          disableGutters
          elevation={0}
          sx={{
            mb: 1,
            backgroundColor: "transparent",
            border: `1px solid ${tk.border.default}`,
            borderRadius: "6px",
            "&:before": { display: "none" },
          }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ fontSize: "1rem", color: tk.text.muted }} />}>
            <Typography sx={{ fontSize: "0.75rem", fontWeight: 600, color: tk.text.secondary }}>
              {t("graph.detailPanel.claimMetadataTitle")}
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ pt: 0 }}>
            <Typography component="pre" sx={graphDetailCodePreSx(tk, compact)}>
              {claimMetadataFormatted}
            </Typography>
          </AccordionDetails>
        </Accordion>
      ) : null}
    </>
  );
}
