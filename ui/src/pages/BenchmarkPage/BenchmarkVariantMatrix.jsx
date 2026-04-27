import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../i18n/useI18n.js";

import BenchmarkVariantMatrixCell from "./BenchmarkVariantMatrixCell.jsx";

/**
 * @param {{ session: Record<string, any>, selectedExperimentId: string | null, selectedVariantId: string | null, onSelectCell: (experimentId: string, variantId: string) => void, onOpenWorkbench?: (runId: string) => void }} props
 */
export default function BenchmarkVariantMatrix({
  session,
  selectedExperimentId,
  selectedVariantId,
  onSelectCell,
  onOpenWorkbench,
}) {
  const tk = useTheme().appTokens;
  const { t } = useI18n();
  if (!session?.rows?.length) return null;
  if (!session.variantIds?.length) return null;

  return (
    <Box
      sx={{
        border: `1px solid ${tk.border.default}`,
        borderRadius: 1.5,
        overflowX: "auto",
        backgroundColor: tk.surface.panel,
      }}
    >
      <Box
        sx={{
          minWidth: 720,
          display: "grid",
          gridTemplateColumns: `minmax(220px, 1.15fr) repeat(${session.variantIds.length}, minmax(180px, 1fr))`,
          gap: 0,
        }}
      >
        <Box sx={{ p: 1.5, borderBottom: `1px solid ${tk.border.default}` }}>
          <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary }}>
            {t("benchmarkPage.analysis.matrix.experiments")}
          </Typography>
        </Box>
        {session.variantIds.map((variantId) => (
          <Box key={variantId} sx={{ p: 1.5, borderBottom: `1px solid ${tk.border.default}` }}>
            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: tk.text.primary }}>{variantId}</Typography>
            <Typography sx={{ mt: 0.35, fontSize: "0.75rem", color: tk.text.secondary }}>
              {t("benchmarkPage.analysis.matrix.variantColumn")}
            </Typography>
          </Box>
        ))}

        {session.rows.map((row) => (
          <React.Fragment key={row.experimentId}>
            <Box
              sx={{
                p: 1.5,
                borderTop: `1px solid ${tk.border.default}`,
                backgroundColor: tk.surface.panel,
              }}
            >
              <Typography sx={{ fontWeight: 600, color: tk.text.primary }}>
                {t(row.experiment.titleKey)}
              </Typography>
              <Typography sx={{ mt: 0.5, fontSize: "0.75rem", color: tk.text.secondary, lineHeight: 1.5 }}>
                {t(row.experiment.descriptionKey)}
              </Typography>
            </Box>
            {row.variants.map((cell) => (
              <Box key={`${row.experimentId}-${cell.variantId}`} sx={{ p: 1, borderTop: `1px solid ${tk.border.default}` }}>
                <BenchmarkVariantMatrixCell
                  experimentId={row.experimentId}
                  cell={cell}
                  selected={selectedExperimentId === row.experimentId && selectedVariantId === cell.variantId}
                  onSelect={() => onSelectCell(row.experimentId, cell.variantId)}
                  onOpenWorkbench={onOpenWorkbench}
                />
              </Box>
            ))}
          </React.Fragment>
        ))}
      </Box>
    </Box>
  );
}
