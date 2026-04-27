import React, { useMemo } from "react";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormGroup from "@mui/material/FormGroup";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorPrimaryButton, CursorSmallButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";

import { buildGroupJobs } from "./benchmarkRunGroup.js";
import { getUiRunnableExperiments } from "./experimentCatalog.js";

/**
 * @param {object} props
 * @param {string[]} props.selectedExperimentIds
 * @param {(id: string, checked: boolean) => void} props.onToggleExperiment
 * @param {string[]} props.selectedModelProfileIds
 * @param {(profileId: string, checked: boolean) => void} props.onToggleModelProfile
 * @param {Array<{ profile_id: string, label?: string }>} props.profileOptions
 * @param {() => void} props.onStartBatch
 * @param {boolean} props.isStarting
 * @param {string | null} props.batchError
 * @param {() => void} [props.onClearBatchError]
 * @param {() => void} [props.onOpenAnalysis]
 */
export default function RunLabGroupedExecutionPanel({
  selectedExperimentIds,
  onToggleExperiment,
  selectedModelProfileIds,
  onToggleModelProfile,
  profileOptions,
  onStartBatch,
  isStarting,
  batchError,
  onClearBatchError,
  onOpenAnalysis,
  canOpenAnalysis,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const uiExperiments = useMemo(() => getUiRunnableExperiments(), []);
  const previewJobs = useMemo(
    () => buildGroupJobs(selectedExperimentIds, selectedModelProfileIds),
    [selectedExperimentIds, selectedModelProfileIds],
  );

  return (
    <Box
      sx={{
        border: `1px solid ${tk.border.default}`,
        borderRadius: "6px",
        backgroundColor: tk.surface.panel,
        p: 1.5,
        display: "flex",
        flexDirection: "column",
        gap: 1.25,
        mb: 2,
      }}
    >
      <Typography sx={{ fontWeight: 600, fontSize: "0.875rem" }}>{t("benchmarkPage.runLab.grouped.title")}</Typography>
      <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, lineHeight: 1.5 }}>
        {t("benchmarkPage.runLab.grouped.hint")}
      </Typography>

      <Box>
        <Typography sx={{ fontWeight: 600, fontSize: "0.75rem", color: tk.text.muted, mb: 0.5 }}>
          {t("benchmarkPage.runLab.grouped.experiments")}
        </Typography>
        <FormGroup sx={{ gap: 0.25 }}>
          {uiExperiments.map((exp) => (
            <FormControlLabel
              key={exp.id}
              sx={{ alignItems: "flex-start", mr: 0 }}
              control={
                <Checkbox
                  size="small"
                  checked={selectedExperimentIds.includes(exp.id)}
                  onChange={(e) => onToggleExperiment(exp.id, e.target.checked)}
                />
              }
              label={
                <Box>
                  <Typography sx={{ fontSize: "0.8125rem" }}>{t(exp.titleKey)}</Typography>
                  <Typography sx={{ fontSize: "0.68rem", color: tk.text.muted }}>{exp.id}</Typography>
                </Box>
              }
            />
          ))}
        </FormGroup>
      </Box>

      <Box>
        <Typography sx={{ fontWeight: 600, fontSize: "0.75rem", color: tk.text.muted, mb: 0.5 }}>
          {t("benchmarkPage.runLab.grouped.variants")}
        </Typography>
        <FormGroup sx={{ gap: 0.25 }}>
          {profileOptions.map((p) => (
            <FormControlLabel
              key={p.profile_id}
              sx={{ mr: 0 }}
              control={
                <Checkbox
                  size="small"
                  checked={selectedModelProfileIds.includes(p.profile_id)}
                  onChange={(e) => onToggleModelProfile(p.profile_id, e.target.checked)}
                />
              }
              label={<Typography sx={{ fontSize: "0.8125rem" }}>{p.label || p.profile_id}</Typography>}
            />
          ))}
        </FormGroup>
      </Box>

      <Box sx={{ borderTop: `1px solid ${tk.border.default}`, pt: 1 }}>
        <Typography sx={{ fontWeight: 600, fontSize: "0.75rem", color: tk.text.muted, mb: 0.5 }}>
          {t("benchmarkPage.runLab.grouped.preview", { count: String(previewJobs.length) })}
        </Typography>
        {previewJobs.length === 0 ? (
          <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary }}>{t("benchmarkPage.runLab.grouped.previewEmpty")}</Typography>
        ) : (
          <Box component="ul" sx={{ m: 0, pl: 2, fontSize: "0.72rem", color: tk.text.secondary }}>
            {previewJobs.slice(0, 12).map((j) => (
              <li key={`${j.experimentId}-${j.modelProfileId}-${j.family}`}>
                {j.experimentId} · {j.family} · {j.modelProfileId} · {j.launcherScope}
              </li>
            ))}
            {previewJobs.length > 12 ? (
              <Typography component="li" sx={{ listStyle: "none", mt: 0.5 }}>
                … +{previewJobs.length - 12} {t("benchmarkPage.runLab.grouped.more")}
              </Typography>
            ) : null}
          </Box>
        )}
      </Box>

      {batchError ? (
        <Typography sx={{ color: tk.state.dangerFg, fontSize: "0.75rem" }} role="alert">
          {batchError}
          {onClearBatchError ? (
            <CursorSmallButton size="small" sx={{ ml: 1 }} onClick={onClearBatchError}>
              {t("benchmarkPage.runLab.grouped.dismissError")}
            </CursorSmallButton>
          ) : null}
        </Typography>
      ) : null}

      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
        <CursorPrimaryButton disabled={isStarting || previewJobs.length === 0} onClick={onStartBatch}>
          {t("benchmarkPage.runLab.grouped.startBatch")}
        </CursorPrimaryButton>
        <CursorSmallButton size="small" disabled={!canOpenAnalysis} onClick={() => onOpenAnalysis?.()}>
          {t("benchmarkPage.runLab.grouped.openAnalysis")}
        </CursorSmallButton>
      </Box>
    </Box>
  );
}
