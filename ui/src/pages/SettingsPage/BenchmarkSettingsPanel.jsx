import React, { useCallback, useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import { Link } from "react-router-dom";
import { useTheme } from "@mui/material/styles";

import { CursorPrimaryButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import BenchmarkAdvancedModelOptions from "../BenchmarkPage/BenchmarkAdvancedModelOptions.jsx";
import BenchmarkModelSelector from "../BenchmarkPage/BenchmarkModelSelector.jsx";
import { settingsCardSx } from "../../theme/settingsFormSx.js";

const FAMILIES = ["layer1", "layer2", "graph"];

function familyPrefsFromSnapshot(benchmark, family) {
  const row = benchmark?.by_family?.[family] || {};
  return {
    model_profile: typeof row.model_profile === "string" ? row.model_profile : "env_default",
    custom_model_id: typeof row.custom_model_id === "string" ? row.custom_model_id : "",
    gold_source: typeof row.gold_source === "string" ? row.gold_source : "curated_gold",
    threshold_profile: typeof row.threshold_profile === "string" ? row.threshold_profile : "from_gold",
    base_url_override: typeof row.base_url_override === "string" ? row.base_url_override : "",
    api_key_env_name: typeof row.api_key_env_name === "string" ? row.api_key_env_name : "",
  };
}

function buildDraftFromBenchmark(benchmark) {
  const out = {};
  for (const f of FAMILIES) {
    out[f] = familyPrefsFromSnapshot(benchmark, f);
  }
  return out;
}

/**
 * @param {object} props
 * @param {object | null | undefined} props.benchmark
 * @param {boolean} props.saving
 * @param {string} props.saveError
 * @param {(payload: { by_family: Record<string, object> }) => Promise<void>} props.onSave
 * @param {(dirty: boolean) => void} props.onDirtyChange
 */
export default function BenchmarkSettingsPanel({ benchmark, saving, saveError, onSave, onDirtyChange }) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const cardSx = useMemo(() => settingsCardSx(tk), [tk]);
  const handleModelsLoaded = useCallback(() => {}, []);
  const benchmarkSyncKey = useMemo(() => JSON.stringify(benchmark ?? null), [benchmark]);
  const [tab, setTab] = useState(0);
  const family = FAMILIES[tab] || "layer1";
  const [draftByFamily, setDraftByFamily] = useState(() => buildDraftFromBenchmark(benchmark));
  const [baselineJson, setBaselineJson] = useState(() => JSON.stringify(buildDraftFromBenchmark(benchmark)));

  /* eslint-disable react-hooks/set-state-in-effect -- hydrate when server benchmark payload changes (e.g. after save) */
  useEffect(() => {
    const next = buildDraftFromBenchmark(benchmark);
    const serialized = JSON.stringify(next);
    setDraftByFamily(next);
    setBaselineJson(serialized);
    // Intentionally depend on benchmarkSyncKey only: `benchmark` ref can change without payload change.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- benchmark read here; sync key is content hash
  }, [benchmarkSyncKey]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const dirty = useMemo(() => JSON.stringify(draftByFamily) !== baselineJson, [baselineJson, draftByFamily]);

  useEffect(() => {
    onDirtyChange?.(dirty);
  }, [dirty, onDirtyChange]);

  const updateFamilyField = useCallback((fam, key, value) => {
    setDraftByFamily((prev) => ({
      ...prev,
      [fam]: {
        ...prev[fam],
        [key]: value,
      },
    }));
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      await onSave({ by_family: draftByFamily });
      setBaselineJson(JSON.stringify(draftByFamily));
    } catch {
      /* Parent sets saveError; keep draft and dirty state */
    }
  }

  const row = draftByFamily[family] || familyPrefsFromSnapshot(null, family);
  const isLayer2 = family === "layer2";
  const isGraph = family === "graph";

  return (
    <Box
      component="form"
      onSubmit={handleSubmit}
      sx={{
        ...cardSx,
        padding: 2.5,
        maxWidth: 720,
      }}
    >
      <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>
        {t("settings.benchmark.title")}
      </Typography>
      <Typography sx={{ marginTop: 1, fontSize: "0.8125rem", color: tk.text.secondary, lineHeight: 1.6 }}>
        {t("settings.benchmark.desc")}
      </Typography>
      <Box sx={{ marginTop: 1, fontSize: "0.8125rem", color: tk.text.secondary, lineHeight: 1.6 }}>
        {t("settings.benchmark.caseSelectionHint")}{" "}
        <Typography component={Link} to="/admin/benchmarks?tab=run-lab" sx={{ color: tk.accent.fg, fontSize: "0.8125rem" }}>
          {t("settings.benchmark.openLaunch")}
        </Typography>
      </Box>

      {saveError ? (
        <Alert
          severity="error"
          sx={{
            marginTop: 2,
            backgroundColor: tk.surface.subtle,
            border: `1px solid ${tk.border.default}`,
          }}
        >
          <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary }}>{saveError}</Typography>
        </Alert>
      ) : null}

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ marginTop: 2, minHeight: 36, "& .MuiTab-root": { fontSize: "0.8125rem", minHeight: 36, py: 0.5 } }}
      >
        <Tab label={t("settings.benchmark.family.layer1")} />
        <Tab label={t("settings.benchmark.family.layer2")} />
        <Tab label={t("settings.benchmark.family.graph")} />
      </Tabs>

      <Box sx={{ marginTop: 2, display: "flex", flexDirection: "column", gap: 2 }}>
        <Box>
          <Typography sx={{ color: tk.text.secondary, mb: 0.5, fontSize: "0.75rem" }}>
            {t("benchmarkPage.runLab.modelProfile")}
          </Typography>
          <BenchmarkModelSelector
            family={family}
            value={row.model_profile}
            customModelId={row.custom_model_id}
            onChange={(nextValue) => updateFamilyField(family, "model_profile", nextValue || "env_default")}
            onCustomModelIdChange={(value) => updateFamilyField(family, "custom_model_id", value)}
            onModelsLoaded={handleModelsLoaded}
          />
        </Box>

        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 1.5 }}>
          <Box>
            <Typography sx={{ color: tk.text.secondary, mb: 0.5, fontSize: "0.75rem" }}>
              {t("benchmarkPage.runLab.goldSource")}
            </Typography>
            <Select
              size="small"
              fullWidth
              value={isLayer2 ? "semantic_gold" : row.gold_source}
              disabled={isLayer2 || isGraph}
              onChange={(e) => updateFamilyField(family, "gold_source", e.target.value)}
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
              value={isLayer2 ? "from_gold" : row.threshold_profile}
              disabled={isLayer2 || isGraph}
              onChange={(e) => updateFamilyField(family, "threshold_profile", e.target.value)}
            >
              <MenuItem value="from_gold">from_gold</MenuItem>
              <MenuItem value="student_mistral">student_mistral</MenuItem>
            </Select>
          </Box>
        </Box>

        <BenchmarkAdvancedModelOptions
          baseUrlOverride={row.base_url_override}
          apiKeyEnvName={row.api_key_env_name}
          onBaseUrlOverrideChange={(value) => updateFamilyField(family, "base_url_override", value)}
          onApiKeyEnvNameChange={(value) => updateFamilyField(family, "api_key_env_name", value)}
        />

        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", alignItems: "center" }}>
          <CursorPrimaryButton type="submit" disabled={saving || !dirty}>
            {t("settings.benchmark.save")}
          </CursorPrimaryButton>
        </Box>
      </Box>
    </Box>
  );
}
