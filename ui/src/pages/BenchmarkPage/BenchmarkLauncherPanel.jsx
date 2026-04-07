import React, { useState } from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";

import { CursorButton, CursorPrimaryButton } from "../../components/common/index.js";
import BenchmarkAdvancedModelOptions from "./BenchmarkAdvancedModelOptions.jsx";
import BenchmarkModelSelector from "./BenchmarkModelSelector.jsx";
import BenchmarkRunConfigSummary from "./BenchmarkRunConfigSummary.jsx";
import BenchmarkRunScopeSelector from "./BenchmarkRunScopeSelector.jsx";

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
}) {
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const isGraphCatalog = benchmarkFamily === "graph";
  const canRunSelected = (familyPrefs?.launcherScope || "selected") !== "selected" || (familyPrefs?.selectedCaseIds?.length || 0) > 0;

  return (
    <Box
      sx={{
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: 1.5,
        backgroundColor: "#141414",
        padding: 1.5,
        display: "flex",
        flexDirection: "column",
        gap: 1.5,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
        <Typography sx={{ fontWeight: 600 }}>
          {isGraphCatalog ? "Graph-v1 catalog" : "Model-aware benchmark launcher"}
        </Typography>
        <Select
          size="small"
          value={benchmarkFamily}
          onChange={(e) => onFamilyChange?.(e.target.value)}
          sx={{ minWidth: 140 }}
        >
          <MenuItem value="layer1">layer1</MenuItem>
          <MenuItem value="layer2">layer2</MenuItem>
          <MenuItem value="graph">graph (CLI)</MenuItem>
        </Select>
      </Box>

      {isGraphCatalog ? (
        <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem" }}>
          Graph benchmark execution remains CLI-first. You can browse cases here, but runs must be started from the CLI.
        </Typography>
      ) : null}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.3fr) minmax(180px, 0.8fr) minmax(180px, 0.8fr)",
          gap: 1,
        }}
      >
        <Box>
          <Typography sx={{ color: "rgba(255,255,255,0.6)", mb: 0.5, fontSize: "0.75rem" }}>
            Model profile
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
          <Typography sx={{ color: "rgba(255,255,255,0.6)", mb: 0.5, fontSize: "0.75rem" }}>
            Gold source
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
          <Typography sx={{ color: "rgba(255,255,255,0.6)", mb: 0.5, fontSize: "0.75rem" }}>
            Threshold profile
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
        <Typography sx={{ color: "rgba(255,255,255,0.5)", fontSize: "0.75rem" }}>
          Effective defaults: role {modelMeta.role || "generic"} | model {modelMeta.model_id || "from environment"} | gold{" "}
          {modelMeta.default_gold_source || "curated_gold"} | threshold {modelMeta.default_threshold_profile || "from_gold"}
        </Typography>
      ) : null}

      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
        <CursorButton onClick={() => setAdvancedOpen((prev) => !prev)}>
          {advancedOpen ? "Hide advanced options" : "Show advanced options"}
        </CursorButton>
      </Box>

      <Collapse in={advancedOpen}>
        <BenchmarkAdvancedModelOptions
          baseUrlOverride={familyPrefs.baseUrlOverride}
          apiKeyEnvName={familyPrefs.apiKeyEnvName}
          onBaseUrlOverrideChange={(value) => onFamilyPrefsChange?.("baseUrlOverride", value)}
          onApiKeyEnvNameChange={(value) => onFamilyPrefsChange?.("apiKeyEnvName", value)}
        />
      </Collapse>

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
            <Typography key={message} sx={{ color: "rgba(239,68,68,0.9)", fontSize: "0.75rem" }} role="alert">
              {message}
            </Typography>
          ))}
        </Box>
      ) : null}

      {pendingSummary ? <BenchmarkRunConfigSummary summary={pendingSummary} title="Pending execution config" /> : null}

      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
        <CursorPrimaryButton disabled={isGraphCatalog || !canRunSelected || validationErrors?.length > 0} onClick={onStartRun}>
          Start {familyPrefs.launcherScope === "selected" ? `selected (${familyPrefs.selectedCaseIds?.length || 0})` : familyPrefs.launcherScope}
        </CursorPrimaryButton>
      </Box>
    </Box>
  );
}
