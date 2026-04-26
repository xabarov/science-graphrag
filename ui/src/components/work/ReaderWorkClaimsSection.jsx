import React, { useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import Collapse from "@mui/material/Collapse";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";

import { CursorSmallButton } from "../common/index.js";
import { useI18n } from "../../i18n/I18nContext.jsx";
import ReaderClaimsListItems from "./ReaderClaimsListItems.jsx";
import { useReaderClaimsFilters } from "./useReaderClaimsFilters.js";
import { useWorkClaims } from "./useWorkClaims.js";

/**
 * Claims block for standalone Reader (VITE_CLAIMS_ENABLED). Lazy fetch on expand.
 * @param {{ workId: string }} props
 */
export default function ReaderWorkClaimsSection({ workId }) {
  const { t } = useI18n();
  const [claimsOpen, setClaimsOpen] = useState(false);
  const { items, loading, error, fetchPhase } = useWorkClaims(workId, {
    enabled: true,
    fetchPolicy: "deferred",
    shouldFetch: claimsOpen,
  });
  const {
    claimTypeFilter,
    setClaimTypeFilter,
    polarityFilter,
    setPolarityFilter,
    claimTypeOptions,
    polarityOptions,
    filteredClaims,
  } = useReaderClaimsFilters(items);

  const showClaimsFetchedEmpty =
    claimsOpen && fetchPhase === "ready" && !loading && !error && items.length === 0;

  return (
    <Box sx={{ mb: 2, p: 1.5, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#161616" }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1, mb: 0.5 }}>
        <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>{t("readerBody.claimsTitle")}</Typography>
        <CursorSmallButton type="button" onClick={() => setClaimsOpen((o) => !o)} sx={{ fontSize: "0.75rem" }}>
          {claimsOpen ? t("readerBody.hide") : t("readerBody.show")}
        </CursorSmallButton>
      </Box>
      <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.42)", mb: 1 }}>{t("readerBody.claimsHint")}</Typography>
      <Collapse in={claimsOpen}>
        {loading ? (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 1 }}>
            <CircularProgress size={20} sx={{ color: "rgba(129,140,248,0.9)" }} />
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}>{t("readerBody.claimsLoading")}</Typography>
          </Box>
        ) : null}
        {error ? (
          <Alert severity="warning" sx={{ fontSize: "0.75rem" }}>
            {error}
          </Alert>
        ) : null}
        {showClaimsFetchedEmpty ? (
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}>{t("readerBody.claimsEmpty")}</Typography>
        ) : null}
        {!loading && !error && items.length > 0 ? (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1.25, mt: 0.5 }}>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 0.25 }}>
              <ToggleButtonGroup
                size="small"
                exclusive
                value={claimTypeFilter}
                onChange={(_e, v) => {
                  if (v) setClaimTypeFilter(v);
                }}
                sx={{ "& .MuiToggleButton-root": { fontSize: "0.7rem", py: 0.15, px: 0.8, textTransform: "none" } }}
              >
                <ToggleButton value="all">{t("readerBody.claimFilterAllTypes")}</ToggleButton>
                {claimTypeOptions.map((opt) => (
                  <ToggleButton key={`ct-${opt}`} value={opt}>
                    {opt}
                  </ToggleButton>
                ))}
              </ToggleButtonGroup>
              <ToggleButtonGroup
                size="small"
                exclusive
                value={polarityFilter}
                onChange={(_e, v) => {
                  if (v) setPolarityFilter(v);
                }}
                sx={{ "& .MuiToggleButton-root": { fontSize: "0.7rem", py: 0.15, px: 0.8, textTransform: "none" } }}
              >
                <ToggleButton value="all">{t("readerBody.claimFilterAllPolarities")}</ToggleButton>
                {polarityOptions.map((opt) => (
                  <ToggleButton key={`cp-${opt}`} value={opt}>
                    {opt}
                  </ToggleButton>
                ))}
              </ToggleButtonGroup>
            </Box>
            {filteredClaims.length === 0 ? (
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}>{t("readerBody.claimsNoFilterMatch")}</Typography>
            ) : null}
            {filteredClaims.length > 0 ? <ReaderClaimsListItems layout="reader" claims={filteredClaims} /> : null}
          </Box>
        ) : null}
      </Collapse>
    </Box>
  );
}
