import React, { useState } from "react";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { useTheme } from "@mui/material/styles";

import { CursorPrimaryButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import BenchmarkAdvancedModelOptions from "./BenchmarkAdvancedModelOptions.jsx";
import BenchmarkModelSelector from "./BenchmarkModelSelector.jsx";
import BenchmarkRunConfigSummary from "./BenchmarkRunConfigSummary.jsx";
import BenchmarkRunScopeSelector from "./BenchmarkRunScopeSelector.jsx";

const LAUNCHER_ADVANCED_PANEL_ID = "benchmark-launcher-advanced-panel";

/**
 * @param {object} props
 * @param {string} props.benchmarkFamily
 * @param {object} props.familyPrefs
 * @param {boolean} props.loadingCases
 * @param {object[]} props.mergeSafeCases
 * @param {object[]} props.nightlyCases
 * @param {string} props.nightlyLabel
 * @param {string[]} [props.validationErrors]
 * @param {object | null} [props.modelMeta]
 * @param {object | null} [props.pendingSummary]
 * @param {(family: string) => void} [props.onFamilyChange]
 * @param {(key: string, value: unknown, opts?: object) => void} [props.onFamilyPrefsChange]
 * @param {(models: unknown) => void} [props.onModelsLoaded]
 * @param {(caseId: string) => void} [props.onToggleCase]
 * @param {() => void} [props.onStartRun]
 * @param {boolean} [props.startRunDisabled]
 */
export default function BenchmarkLauncherPanel({
  benchmarkFamily,
  familyPrefs,
  loadingCases,
  mergeSafeCases,
  nightlyCases,
  nightlyLabel,
  validationErrors,
  modelMeta,
  pendingSummary,
  onFamilyChange,
  onFamilyPrefsChange,
  onModelsLoaded,
  onToggleCase,
  onStartRun,
  startRunDisabled = false,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const [advancedExpanded, setAdvancedExpanded] = useState(false);
  const isGraphCatalog = benchmarkFamily === "graph";
  const canRunSelected =
    (familyPrefs?.launcherScope || "selected") !== "selected" || (familyPrefs?.selectedCaseIds?.length || 0) > 0;

  const familyLabelKey =
    benchmarkFamily === "layer2"
      ? "benchmarkPage.runLab.familyApi.layer2"
      : benchmarkFamily === "graph"
        ? "benchmarkPage.runLab.familyApi.graph"
        : "benchmarkPage.runLab.familyApi.layer1";

  const scope = familyPrefs?.launcherScope || "selected";
  const startLabel =
    scope === "selected"
      ? t("benchmarkPage.runLab.startSelected", { count: familyPrefs?.selectedCaseIds?.length || 0 })
      : t("benchmarkPage.runLab.startScope", { scope });

  return (
    <Box
      sx={{
        border: `1px solid ${tk.border.default}`,
        borderRadius: 1.5,
        backgroundColor: tk.surface.sidebar,
        padding: 1.5,
        display: "flex",
        flexDirection: "column",
        gap: 1.5,
      }}
    >
      <Typography sx={{ fontWeight: 600 }}>{t("benchmarkPage.runLab.launcherCardTitle")}</Typography>

      {isGraphCatalog ? (
        <Typography sx={{ color: tk.text.muted, fontSize: "0.8125rem" }}>{t("benchmarkPage.runLab.graphCatalogBody")}</Typography>
      ) : null}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.3fr) minmax(180px, 0.8fr) minmax(180px, 0.8fr)",
          gap: 1,
        }}
      >
        <Box>
          <Typography sx={{ color: tk.text.secondary, mb: 0.5, fontSize: "0.75rem" }}>
            {t("benchmarkPage.runLab.modelProfile")}
          </Typography>
          <BenchmarkModelSelector
            family={benchmarkFamily}
            value={familyPrefs.modelProfile}
            customModelId={familyPrefs.customModelId}
            onChange={(nextValue, profile) => onFamilyPrefsChange?.("modelProfile", nextValue, { profile })}
            onCustomModelIdChange={(value) => onFamilyPrefsChange?.("customModelId", value)}
            onModelsLoaded={onModelsLoaded}
          />
        </Box>

        <Box>
          <Typography sx={{ color: tk.text.secondary, mb: 0.5, fontSize: "0.75rem" }}>
            {t("benchmarkPage.runLab.goldSource")}
          </Typography>
          <Select
            size="small"
            fullWidth
            value={benchmarkFamily === "layer2" ? "semantic_gold" : familyPrefs.goldSource}
            disabled={benchmarkFamily === "layer2" || isGraphCatalog}
            onChange={(e) => onFamilyPrefsChange?.("goldSource", e.target.value, { markOverride: true })}
          >
            <MenuItem value="curated_gold">curated_gold</MenuItem>
            <MenuItem value="teacher_gold">teacher_gold</MenuItem>
          </Select>
        </Box>

        <Box>
          <Typography sx={{ color: tk.text.secondary, mb: 0.5, fontSize: "0.75rem" }}>
            {t("benchmarkPage.runLab.thresholdProfile")}
          </Typography>
          <Select
            size="small"
            fullWidth
            value={benchmarkFamily === "layer2" ? "from_gold" : familyPrefs.thresholdProfile}
            disabled={benchmarkFamily === "layer2" || isGraphCatalog}
            onChange={(e) => onFamilyPrefsChange?.("thresholdProfile", e.target.value, { markOverride: true })}
          >
            <MenuItem value="from_gold">from_gold</MenuItem>
            <MenuItem value="student_mistral">student_mistral</MenuItem>
          </Select>
        </Box>
      </Box>

      {modelMeta ? (
        <Typography sx={{ color: tk.text.muted, fontSize: "0.75rem" }}>
          {t("benchmarkPage.runLab.effectiveDefaults", {
            role: modelMeta.role || "generic",
            model: modelMeta.model_id || "from environment",
            gold: modelMeta.default_gold_source || "curated_gold",
            threshold: modelMeta.default_threshold_profile || "from_gold",
          })}
        </Typography>
      ) : null}

      <Accordion
        expanded={advancedExpanded}
        onChange={(_, expandedNext) => setAdvancedExpanded(expandedNext)}
        disableGutters
        elevation={0}
        sx={{
          border: `1px solid ${tk.border.default}`,
          borderRadius: 1,
          backgroundColor: tk.surface.panel,
          "&:before": { display: "none" },
        }}
      >
        <AccordionSummary
          expandIcon={<ExpandMoreIcon sx={{ fontSize: "1.1rem" }} />}
          aria-controls={LAUNCHER_ADVANCED_PANEL_ID}
          id="benchmark-launcher-advanced-summary"
        >
          <Typography sx={{ fontSize: "0.8125rem", fontWeight: 600 }}>{t("benchmarkPage.runLab.advancedAccordion")}</Typography>
        </AccordionSummary>
        <AccordionDetails
          id={LAUNCHER_ADVANCED_PANEL_ID}
          sx={{ pt: 0, display: "flex", flexDirection: "column", gap: 1.5 }}
          role="region"
          aria-labelledby="benchmark-launcher-advanced-summary"
        >
          <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1 }}>
            <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary }}>{t(familyLabelKey)}</Typography>
            <Select
              size="small"
              value={benchmarkFamily}
              onChange={(e) => onFamilyChange?.(e.target.value)}
              sx={{ minWidth: 160 }}
              title={`API: ${benchmarkFamily}`}
              inputProps={{ "aria-label": t("benchmarkPage.runLab.familySelectAria") }}
            >
              <MenuItem value="layer1">{t("benchmarkPage.runLab.familyApi.layer1")}</MenuItem>
              <MenuItem value="layer2">{t("benchmarkPage.runLab.familyApi.layer2")}</MenuItem>
              <MenuItem value="graph">{t("benchmarkPage.runLab.familyApi.graph")}</MenuItem>
            </Select>
            <Typography sx={{ fontSize: "0.68rem", color: tk.text.muted, fontFamily: "monospace" }}>
              API: {benchmarkFamily}
            </Typography>
          </Box>
          <BenchmarkAdvancedModelOptions
            baseUrlOverride={familyPrefs.baseUrlOverride}
            apiKeyEnvName={familyPrefs.apiKeyEnvName}
            onBaseUrlOverrideChange={(value) => onFamilyPrefsChange?.("baseUrlOverride", value)}
            onApiKeyEnvNameChange={(value) => onFamilyPrefsChange?.("apiKeyEnvName", value)}
          />
        </AccordionDetails>
      </Accordion>

      <BenchmarkRunScopeSelector
        mergeSafeCases={mergeSafeCases}
        nightlyCases={nightlyCases}
        nightlyLabel={nightlyLabel}
        loadingCases={loadingCases}
        selectedCaseIds={familyPrefs.selectedCaseIds || []}
        launcherScope={familyPrefs.launcherScope}
        onScopeChange={(value) => onFamilyPrefsChange?.("launcherScope", value)}
        onToggleCase={onToggleCase}
      />

      {validationErrors?.length ? (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
          {validationErrors.map((message) => (
            <Typography key={message} sx={{ color: tk.state.dangerFg, fontSize: "0.75rem" }} role="alert">
              {message}
            </Typography>
          ))}
        </Box>
      ) : null}

      {pendingSummary ? (
        <BenchmarkRunConfigSummary summary={pendingSummary} title={t("benchmarkPage.runLab.pendingConfigTitle")} />
      ) : null}

      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
        <CursorPrimaryButton
          disabled={startRunDisabled || isGraphCatalog || !canRunSelected || validationErrors?.length > 0}
          onClick={onStartRun}
        >
          {startLabel}
        </CursorPrimaryButton>
      </Box>
    </Box>
  );
}
