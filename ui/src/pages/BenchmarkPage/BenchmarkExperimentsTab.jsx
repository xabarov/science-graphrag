import React from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorSmallButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";

import {
  EXPERIMENT_PACKS,
  benchmarkTypeLabelKey,
  compareModeLabelKey,
  getExperimentById,
  getLauncherPresetForExperiment,
  runnableSurfaceLabelKey,
  RUN_MODE_GROUPED,
} from "./experimentCatalog.js";

/**
 * @param {object} props
 * @param {(opts: { tabIndex: number, analysisView?: "results"|"compare"|"workbench", experimentId?: string | null, runMode?: "single"|"grouped", packId?: string | null }) => void} props.onNavigate
 */
export default function BenchmarkExperimentsTab({ onNavigate }) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;

  return (
    <Box sx={{ p: 2 }}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.9375rem", mb: 0.75 }}>{t("benchmarkPage.experiments.title")}</Typography>
      <Typography sx={{ fontSize: "0.8125rem", color: tk.text.secondary, lineHeight: 1.55, maxWidth: 920, mb: 2 }}>
        {t("benchmarkPage.experiments.intro")}
      </Typography>
      <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, mb: 2 }}>{t("benchmarkPage.experiments.variantHint")}</Typography>

      {EXPERIMENT_PACKS.map((pack) => (
        <Box key={pack.id} sx={{ mb: 3 }}>
          <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 0.75, mb: 0.5 }}>
            <Typography sx={{ fontWeight: 600, fontSize: "0.875rem" }}>
              {t(pack.titleKey)} <Box component="span" sx={{ color: tk.text.muted, fontWeight: 500 }}>({pack.id})</Box>
            </Typography>
            {pack.experimentIds.some((eid) => getLauncherPresetForExperiment(eid)) ? (
              <CursorSmallButton
                size="small"
                onClick={() => onNavigate({ tabIndex: 2, runMode: RUN_MODE_GROUPED, packId: pack.id })}
              >
                {t("benchmarkPage.experiments.ctaPackGrouped")}
              </CursorSmallButton>
            ) : null}
          </Box>
          <Typography sx={{ fontSize: "0.8125rem", color: tk.text.secondary, mb: 1.5 }}>{t(pack.descriptionKey)}</Typography>
          <Divider sx={{ mb: 1.5, borderColor: tk.border.default }} />
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
            {pack.experimentIds.map((eid) => {
              const exp = getExperimentById(eid);
              if (!exp) return null;
              return (
                <Box
                  key={eid}
                  sx={{
                    border: `1px solid ${tk.border.default}`,
                    borderRadius: "6px",
                    backgroundColor: tk.surface.panel,
                    p: 1.5,
                  }}
                >
                  <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>{t(exp.titleKey)}</Typography>
                  <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, mb: 0.75 }}>{exp.id}</Typography>
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mb: 0.75 }}>
                    <Chip size="small" label={t(benchmarkTypeLabelKey(exp.benchmarkType))} sx={{ height: 22, fontSize: "0.68rem" }} />
                    <Chip size="small" label={t(runnableSurfaceLabelKey(exp.runnableSurface))} variant="outlined" sx={{ height: 22, fontSize: "0.68rem" }} />
                  </Box>
                  <Typography sx={{ fontSize: "0.8125rem", color: tk.text.secondary, lineHeight: 1.5, mb: 0.75 }}>
                    {t(exp.descriptionKey)}
                  </Typography>
                  <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted }}>{t(exp.defaultScopeKey)}</Typography>
                  <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, mt: 0.25 }}>
                    {t(compareModeLabelKey(exp.recommendedCompareMode))}
                  </Typography>
                  <Typography sx={{ fontSize: "0.72rem", color: tk.text.secondary, mt: 0.5 }}>
                    {exp.primaryMetricKeys.map((k) => t(k)).join(" · ")}
                  </Typography>
                  {exp.runnableSurface !== "ui" ? (
                    <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, mt: 0.5 }}>
                      {t("benchmarkPage.experiments.notRunnableFromUi")}
                    </Typography>
                  ) : null}
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 1 }}>
                    {exp.runnableSurface === "ui" ? (
                      <CursorSmallButton size="small" onClick={() => onNavigate({ tabIndex: 2, experimentId: exp.id })}>
                        {t("benchmarkPage.experiments.ctaRunLab")}
                      </CursorSmallButton>
                    ) : null}
                    <CursorSmallButton size="small" onClick={() => onNavigate({ tabIndex: 3, analysisView: "results" })}>
                      {t("benchmarkPage.experiments.ctaAnalysis")}
                    </CursorSmallButton>
                  </Box>
                </Box>
              );
            })}
          </Box>
        </Box>
      ))}
    </Box>
  );
}
