import React, { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";

import { CursorSmallButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { useBenchmarkSummary } from "../../hooks/useBenchmarkSummary.js";
import { formatResearchApiError } from "../../services/researchApi.js";

import TrustSignalDrillIn from "./TrustSignalDrillIn.jsx";
import { buildTrustRows, decisionChipSx } from "./trustSignalDrillInHelpers.js";

export { buildTrustRows, decisionChipSx };

/**
 * @param {object} [props]
 * @param {boolean} [props.defaultExpanded] When false, details start collapsed (e.g. Overview diagnostics).
 */
export default function TrustSignalPanel({ defaultExpanded = true } = {}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const { data, error, loading, reload } = useBenchmarkSummary();
  const [expanded, setExpanded] = useState(defaultExpanded);

  const rows = useMemo(() => buildTrustRows(data?.trust_by_family), [data]);

  const phantomCount = useMemo(
    () => rows.filter((r) => r.isPhantom).length,
    [rows],
  );

  if (loading) {
    return (
      <Box sx={{ px: 2, pb: 1 }}>
        <Typography sx={{ color: tk.text.muted, fontSize: "0.8125rem" }}>
          {t("benchmarkPage.trustSignal.loading")}
        </Typography>
      </Box>
    );
  }

  if (error) {
    const is404 = error?.response?.status === 404;
    return (
      <Box sx={{ px: 2, pb: 1 }}>
        <Typography sx={{ color: tk.state.dangerFg, fontSize: "0.8125rem" }}>
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
        border: `1px solid ${tk.border.default}`,
        borderRadius: 1,
        backgroundColor: tk.surface.panel,
        px: 1.5,
        py: 1,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
        <Chip label={data.decision} size="small" sx={decisionChipSx(data.decision, tk)} />
        <Typography sx={{ flex: 1, minWidth: 0, color: tk.text.secondary, fontSize: "0.75rem" }}>
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
      <Typography sx={{ mt: 0.5, color: tk.text.muted, fontSize: "0.7rem" }}>
        {t("benchmarkPage.trustSignal.phantomCount", { count: phantomCount })}
      </Typography>
      <Collapse in={expanded}>
        <Box sx={{ mt: 1, display: "flex", flexDirection: "column", maxHeight: 420, overflow: "auto" }}>
          <TrustSignalDrillIn criteria={data.criteria} trustByFamily={data.trust_by_family} t={t} />
          <Typography
            sx={{
              mt: 0.5,
              mb: 0.5,
              color: tk.text.secondary,
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
                  borderTop: `1px solid ${tk.border.default}`,
                  pt: 0.5,
                }}
              >
                <Typography sx={{ color: tk.text.secondary, fontFamily: "monospace" }}>
                  {r.familyKey}.{r.memberId}
                </Typography>
                <Chip
                  label={r.runtimeMode}
                  size="small"
                  sx={{
                    height: 22,
                    fontSize: "0.7rem",
                    backgroundColor: r.isPhantom ? tk.state.dangerBg : tk.accent.chipReadyBg,
                    border: r.isPhantom ? `1px solid ${tk.state.dangerBorder}` : `1px solid ${tk.accent.softBorder}`,
                    color: r.isPhantom ? tk.state.dangerFg : tk.accent.chipReadyFg,
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
