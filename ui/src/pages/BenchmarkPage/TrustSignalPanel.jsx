import React, { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";

import { CursorSmallButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/I18nContext.jsx";
import { useBenchmarkSummary } from "../../hooks/useBenchmarkSummary.js";
import { formatResearchApiError } from "../../services/researchApi.js";

import TrustSignalDrillIn from "./TrustSignalDrillIn.jsx";
import { buildTrustRows, decisionChipSx } from "./trustSignalDrillInHelpers.js";

export { buildTrustRows, decisionChipSx };

export default function TrustSignalPanel() {
  const { t } = useI18n();
  const { data, error, loading, reload } = useBenchmarkSummary();
  const [expanded, setExpanded] = useState(true);

  const rows = useMemo(() => buildTrustRows(data?.trust_by_family), [data]);

  const phantomCount = useMemo(
    () => rows.filter((r) => r.isPhantom).length,
    [rows],
  );

  if (loading) {
    return (
      <Box sx={{ px: 2, pb: 1 }}>
        <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem" }}>
          {t("benchmarkPage.trustSignal.loading")}
        </Typography>
      </Box>
    );
  }

  if (error) {
    const is404 = error?.response?.status === 404;
    return (
      <Box sx={{ px: 2, pb: 1 }}>
        <Typography sx={{ color: "rgba(239, 68, 68, 0.85)", fontSize: "0.8125rem" }}>
          {is404 ? t("benchmarkPage.trustSignal.missingSummary") : formatResearchApiError(error)}
        </Typography>
        <CursorSmallButton size="small" onClick={() => void reload()} sx={{ mt: 0.5 }}>
          {t("benchmarkPage.trustSignal.retry")}
        </CursorSmallButton>
      </Box>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <Box
      sx={{
        mx: 2,
        mb: 1.5,
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: 1,
        backgroundColor: "#1a1a1a",
        px: 1.5,
        py: 1,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
        <Chip label={data.decision} size="small" sx={decisionChipSx(data.decision)} />
        <Typography sx={{ flex: 1, minWidth: 0, color: "rgba(255,255,255,0.6)", fontSize: "0.75rem" }}>
          {data.reason}
        </Typography>
        <IconButton
          size="small"
          onClick={() => setExpanded((v) => !v)}
          aria-label={t("benchmarkPage.trustSignal.toggleDetailsAria")}
        >
          {expanded ? <ExpandLess /> : <ExpandMore />}
        </IconButton>
        <CursorSmallButton size="small" onClick={() => void reload()}>
          {t("benchmarkPage.trustSignal.refresh")}
        </CursorSmallButton>
      </Box>
      <Typography sx={{ mt: 0.5, color: "rgba(255,255,255,0.45)", fontSize: "0.7rem" }}>
        {t("benchmarkPage.trustSignal.phantomCount", { count: phantomCount })}
      </Typography>
      <Collapse in={expanded}>
        <Box sx={{ mt: 1, display: "flex", flexDirection: "column", maxHeight: 420, overflow: "auto" }}>
          <TrustSignalDrillIn criteria={data.criteria} trustByFamily={data.trust_by_family} t={t} />
          <Typography
            sx={{
              mt: 0.5,
              mb: 0.5,
              color: "rgba(255,255,255,0.7)",
              fontSize: "0.7rem",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.04em",
            }}
          >
            {t("benchmarkPage.trustDrillIn.sectionSuiteMembers")}
          </Typography>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
            {rows.map((r) => (
              <Box
                key={`${r.familyKey}.${r.memberId}`}
                sx={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 0.75,
                  alignItems: "center",
                  fontSize: "0.75rem",
                  borderTop: "1px solid rgba(255,255,255,0.06)",
                  pt: 0.5,
                }}
              >
                <Typography sx={{ color: "rgba(255,255,255,0.75)", fontFamily: "monospace" }}>
                  {r.familyKey}.{r.memberId}
                </Typography>
                <Chip
                  label={r.runtimeMode}
                  size="small"
                  sx={{
                    height: 22,
                    fontSize: "0.7rem",
                    backgroundColor: r.isPhantom ? "rgba(239, 68, 68, 0.12)" : "rgba(99, 102, 241, 0.12)",
                    border: r.isPhantom
                      ? "1px solid rgba(239, 68, 68, 0.2)"
                      : "1px solid rgba(99, 102, 241, 0.25)",
                    color: r.isPhantom ? "rgba(239, 68, 68, 0.9)" : "rgba(129, 140, 248, 0.95)",
                  }}
                />
              </Box>
            ))}
          </Box>
        </Box>
      </Collapse>
    </Box>
  );
}
