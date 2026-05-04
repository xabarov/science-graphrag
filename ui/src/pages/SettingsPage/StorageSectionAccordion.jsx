import React from "react";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

/**
 * @param {{
 *   defaultExpanded?: boolean;
 *   summaryStart: React.ReactNode;
 *   title: string;
 *   subtitle: string;
 *   accordionSx: object;
 *   tk: import("../../theme/appTokensTypes.js").AppTokens;
 *   children: React.ReactNode;
 * }} props
 */
export default function StorageSectionAccordion({ defaultExpanded = true, summaryStart, title, subtitle, accordionSx, tk, children }) {
  return (
    <Accordion
      defaultExpanded={defaultExpanded}
      disableGutters
      elevation={0}
      sx={{
        ...accordionSx,
        "&:before": { display: "none" },
        "&.Mui-expanded": { margin: 0 },
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon sx={{ color: tk.text.muted }} />}
        sx={{
          minHeight: 48,
          px: 1.5,
          "& .MuiAccordionSummary-content": {
            alignItems: "center",
            gap: 1.25,
            marginY: 1,
          },
        }}
      >
        <Box sx={{ color: tk.text.secondary, display: "flex", alignItems: "center" }}>{summaryStart}</Box>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.25, minWidth: 0 }}>
          <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>{title}</Typography>
          <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, lineHeight: 1.45 }}>{subtitle}</Typography>
        </Box>
      </AccordionSummary>
      <AccordionDetails sx={{ px: 2, pb: 2, pt: 0, display: "flex", flexDirection: "column" }}>{children}</AccordionDetails>
    </Accordion>
  );
}
