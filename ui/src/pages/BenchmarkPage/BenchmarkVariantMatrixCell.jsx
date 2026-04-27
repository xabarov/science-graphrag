import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorSmallButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";

function formatMetric(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return Number(value).toFixed(3);
}

/**
 * @param {{ experimentId: string, cell: Record<string, any>, selected: boolean, onSelect: () => void, onOpenWorkbench?: (runId: string) => void }} props
 */
export default function BenchmarkVariantMatrixCell({ experimentId, cell, selected, onSelect, onOpenWorkbench }) {
  const tk = useTheme().appTokens;
  const { t } = useI18n();
  const isMissing = !cell?.runId;
  const summary = cell?.summary;
  const primaryMetric =
    experimentId === "layer2_semantic" ? formatMetric(summary?.avgRecall) : formatMetric(summary?.avgNamesF1);
  const secondaryMetric =
    experimentId === "layer2_semantic"
      ? `${summary?.passCount ?? 0}/${summary?.caseCount ?? 0}`
      : `${summary?.failCount ?? 0}`;

  return (
    <Box
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect();
        }
      }}
      sx={{
        minHeight: 122,
        border: `1px solid ${selected ? tk.accent.fg : tk.border.default}`,
        borderRadius: 1.5,
        p: 1.25,
        backgroundColor: selected ? tk.accent.bg : tk.surface.panel,
        cursor: "pointer",
        transition: "all 0.15s ease",
        "&:hover": {
          borderColor: selected ? tk.accent.fg : tk.border.hover,
          backgroundColor: selected ? tk.accent.bg : tk.surface.subtle,
        },
        "&:focus-visible": {
          outline: `2px solid ${tk.accent.fg}`,
          outlineOffset: 2,
        },
      }}
    >
      <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, textTransform: "uppercase" }}>
        {isMissing ? t("benchmarkPage.analysis.matrix.missing") : cell.status}
      </Typography>
      <Typography sx={{ mt: 0.6, fontSize: "1rem", fontWeight: 600, color: tk.text.primary }}>{primaryMetric}</Typography>
      <Typography sx={{ mt: 0.35, fontSize: "0.75rem", color: tk.text.secondary }}>
        {experimentId === "layer2_semantic"
          ? t("benchmarkPage.analysis.matrix.avgRecall")
          : t("benchmarkPage.analysis.matrix.avgNamesF1")}
      </Typography>
      <Typography sx={{ mt: 1, fontSize: "0.75rem", color: tk.text.secondary }}>
        {experimentId === "layer2_semantic"
          ? t("benchmarkPage.analysis.matrix.passRatio", { value: secondaryMetric })
          : t("benchmarkPage.analysis.matrix.failedCount", { value: secondaryMetric })}
      </Typography>
      {cell?.runId ? (
        <CursorSmallButton
          size="small"
          sx={{ mt: 1 }}
          onClick={(event) => {
            event.stopPropagation();
            onOpenWorkbench?.(cell.runId);
          }}
        >
          {t("benchmarkPage.analysis.openWorkbench")}
        </CursorSmallButton>
      ) : null}
    </Box>
  );
}
