import React, { useMemo } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import TrustAdvisoryFailuresTable from "./TrustAdvisoryFailuresTable.jsx";
import TrustConsistencyWarningsList from "./TrustConsistencyWarningsList.jsx";
import TrustValidationStatusTable from "./TrustValidationStatusTable.jsx";
import {
  collectAdvisoryFailureRows,
  collectConsistencyWarningLines,
  collectValidationStatusRows,
} from "./trustSignalDrillInHelpers.js";

/**
 * Decision-gate drill-in: consistency warnings, validation_status_aggregate per member, advisory failures.
 * @param {{ criteria?: Record<string, unknown>, trustByFamily?: Record<string, unknown>, t: (key: string) => string }} props
 */
export default function TrustSignalDrillIn({ criteria, trustByFamily, t }) {
  const tk = useTheme().appTokens;
  const sectionTitleSx = {
    color: tk.text.secondary,
    fontSize: "0.7rem",
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.04em",
    mb: 0.5,
  };
  const warningLines = useMemo(() => collectConsistencyWarningLines(trustByFamily), [trustByFamily]);
  const validationRows = useMemo(() => collectValidationStatusRows(trustByFamily), [trustByFamily]);
  const advisoryRows = useMemo(() => collectAdvisoryFailureRows(criteria), [criteria]);

  if (!warningLines.length && !validationRows.length && !advisoryRows.length) {
    return null;
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5, mb: 1 }}>
      {warningLines.length ? <TrustConsistencyWarningsList lines={warningLines} t={t} /> : null}

      {validationRows.length ? (
        <Box>
          <Typography sx={sectionTitleSx}>{t("benchmarkPage.trustDrillIn.sectionValidation")}</Typography>
          <TrustValidationStatusTable rows={validationRows} t={t} />
        </Box>
      ) : null}

      {advisoryRows.length ? (
        <Box>
          <Typography sx={sectionTitleSx}>{t("benchmarkPage.trustDrillIn.sectionAdvisoryFailures")}</Typography>
          <TrustAdvisoryFailuresTable rows={advisoryRows} t={t} />
        </Box>
      ) : null}
    </Box>
  );
}
