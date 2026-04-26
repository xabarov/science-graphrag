import React from "react";
import { useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";

import { useI18n } from "../../../i18n/I18nContext.jsx";

export default function CaseDetailArtifactsSection({
  artifacts,
  usesLayer1Gold,
  goldSource,
  onGoldSourceChange,
  onClose,
}) {
  const { t } = useI18n();
  const navigate = useNavigate();

  if (!artifacts) return null;

  const present = t("benchmark.caseDialog.statePresent");
  const missing = t("benchmark.caseDialog.stateMissing");
  const curatedVariant = artifacts.gold_variants?.find((g) => g.id === "curated_gold");
  const teacherVariant = artifacts.gold_variants?.find((g) => g.id === "teacher_gold");

  return (
    <Box sx={{ mb: 2, display: "flex", flexDirection: "column", gap: 1 }}>
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.6)" }}>
        {t("benchmark.caseDialog.artifactsHeading")}
      </Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
        <Chip
          size="small"
          label={t("benchmark.caseDialog.chipArticle", {
            state: artifacts.article?.present ? present : missing,
          })}
          variant="outlined"
        />
        {usesLayer1Gold ? (
          <>
            <Chip
              size="small"
              label={t("benchmark.caseDialog.chipCurated", {
                state: curatedVariant?.present ? present : missing,
              })}
              variant="outlined"
            />
            <Chip
              size="small"
              label={t("benchmark.caseDialog.chipTeacher", {
                state: teacherVariant?.present ? present : missing,
              })}
              variant="outlined"
            />
          </>
        ) : null}
        {artifacts.semantic_gold ? (
          <Chip
            size="small"
            label={t("benchmark.caseDialog.chipSemanticGold", {
              state: artifacts.semantic_gold.present ? present : missing,
            })}
            variant="outlined"
          />
        ) : null}
        {artifacts.semantic_gold_teacher?.present ? (
          <Chip
            size="small"
            label={t("benchmark.caseDialog.chipSemanticGoldTeacherPresent")}
            variant="outlined"
          />
        ) : null}
        {artifacts.last_run_hints?.run_id ? (
          <Chip
            size="small"
            label={t("benchmark.caseDialog.chipLastRun", {
              prefix: String(artifacts.last_run_hints.run_id).slice(0, 8),
              status: artifacts.last_run_hints.status ?? "?",
            })}
            variant="outlined"
            onClick={() => {
              const rid = artifacts.last_run_hints?.run_id;
              if (rid) {
                navigate(`/benchmark?tab=workbench&run=${encodeURIComponent(String(rid))}`);
                onClose?.();
              }
            }}
            sx={{
              borderColor: "rgba(99, 102, 241, 0.35)",
              cursor: "pointer",
            }}
          />
        ) : null}
      </Box>
      {usesLayer1Gold && (curatedVariant?.present || teacherVariant?.present) ? (
        <FormControl size="small" sx={{ minWidth: 220, mt: 0.5 }}>
          <InputLabel id="case-gold-src">{t("benchmark.caseDialog.goldSourceLabel")}</InputLabel>
          <Select
            labelId="case-gold-src"
            label={t("benchmark.caseDialog.goldSourceSelectLabel")}
            value={goldSource}
            onChange={(e) => onGoldSourceChange(e.target.value)}
          >
            <MenuItem value="curated_gold" disabled={!curatedVariant?.present}>
              {t("benchmark.caseDialog.menuCuratedGold")}
            </MenuItem>
            <MenuItem value="teacher_gold" disabled={!teacherVariant?.present}>
              {t("benchmark.caseDialog.menuTeacherGold")}
            </MenuItem>
          </Select>
        </FormControl>
      ) : null}
    </Box>
  );
}
