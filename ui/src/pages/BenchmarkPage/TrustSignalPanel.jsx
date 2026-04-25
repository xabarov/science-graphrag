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

/**
 * Flatten trust_by_family payload into table rows (exported for unit tests).
 * @param {Record<string, { members?: Record<string, object> }>} trustByFamily
 * @returns {Array<{ familyKey: string, memberId: string, runtimeMode: string, isPhantom: boolean }>}
 */
export function buildTrustRows(trustByFamily) {
  const rows = [];
  if (!trustByFamily || typeof trustByFamily !== "object") return rows;
  for (const [familyKey, fam] of Object.entries(trustByFamily)) {
    const members = fam?.members && typeof fam.members === "object" ? fam.members : {};
    for (const [memberId, ts] of Object.entries(members)) {
      if (ts && typeof ts === "object") {
        rows.push({
          familyKey,
          memberId,
          runtimeMode: String(ts.runtime_mode || ""),
          isPhantom: Boolean(ts.is_phantom),
        });
      }
    }
  }
  return rows;
}

/** @param {string} decision */
export function decisionChipSx(decision) {
  const d = String(decision || "").toUpperCase();
  if (d.includes("NO-GO")) {
    return {
      backgroundColor: "rgba(239, 68, 68, 0.12)",
      border: "1px solid rgba(239, 68, 68, 0.25)",
      color: "rgba(239, 68, 68, 0.95)",
      fontWeight: 600,
      fontSize: "0.75rem",
    };
  }
  if (d.includes("CONDITIONAL")) {
    return {
      backgroundColor: "rgba(255,255,255,0.06)",
      border: "1px solid rgba(255,255,255,0.12)",
      color: "rgba(255,255,255,0.85)",
      fontWeight: 600,
      fontSize: "0.75rem",
    };
  }
  return {
    backgroundColor: "rgba(99, 102, 241, 0.15)",
    border: "1px solid rgba(99, 102, 241, 0.3)",
    color: "rgba(129, 140, 248, 0.95)",
    fontWeight: 600,
    fontSize: "0.75rem",
  };
}

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
        <IconButton size="small" onClick={() => setExpanded((v) => !v)} aria-label="toggle trust details">
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
        <Box sx={{ mt: 1, display: "flex", flexDirection: "column", gap: 0.5, maxHeight: 220, overflow: "auto" }}>
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
      </Collapse>
    </Box>
  );
}
