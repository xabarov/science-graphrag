import React, { useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import { Link, useSearchParams } from "react-router-dom";

import AdminPanelSettingsOutlinedIcon from "@mui/icons-material/AdminPanelSettingsOutlined";
import HomeOutlinedIcon from "@mui/icons-material/HomeOutlined";

import { CursorIconAction } from "../components/common/index.js";
import DiagnosticsSettingsPanel from "./SettingsPage/DiagnosticsSettingsPanel.jsx";
import IngestionSettingsPanel from "./SettingsPage/IngestionSettingsPanel.jsx";
import GeneralSettingsPanel from "./SettingsPage/GeneralSettingsPanel.jsx";
import LlmSettingsPanel from "./SettingsPage/LlmSettingsPanel.jsx";
import SecuritySettingsPanel from "./SettingsPage/SecuritySettingsPanel.jsx";
import StorageSettingsPanel from "./SettingsPage/StorageSettingsPanel.jsx";
import BenchmarkSettingsPanel from "./SettingsPage/BenchmarkSettingsPanel.jsx";
import SettingsLayout from "./SettingsPage/SettingsLayout.jsx";
import { PlaceholderSettingsSection } from "./SettingsPage/PlaceholderSettingsSection.jsx";
import { useSettingsPageBootstrap } from "./SettingsPage/useSettingsPageBootstrap.js";
import {
  deleteLlmSecret,
  testLlmConnection,
  updateGeneralSettings,
  updateIngestionSettings,
  updateLlmSettings,
  updateStorageSettings,
  updateBenchmarkSettings,
} from "./SettingsPage/settingsApi.js";
import { formatResearchApiError } from "../services/researchApi.js";
import { useI18n } from "../i18n/useI18n.js";

export default function SettingsPage() {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const [searchParams] = useSearchParams();
  const settingsUrlSearchKey = searchParams.toString();
  const {
    snapshot,
    setSnapshot,
    schema,
    activeSectionId,
    setActiveSectionId,
    loading,
    loadError,
  } = useSettingsPageBootstrap({ settingsUrlSearchKey, t });
  const [saveError, setSaveError] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [dirtyHint, setDirtyHint] = useState(false);
  const [ingestionDirty, setIngestionDirty] = useState(false);
  const [ingestionSaveError, setIngestionSaveError] = useState("");
  const [ingestionSaving, setIngestionSaving] = useState(false);
  const [generalDirty, setGeneralDirty] = useState(false);
  const [generalSaveError, setGeneralSaveError] = useState("");
  const [generalSaving, setGeneralSaving] = useState(false);
  const [storageDirty, setStorageDirty] = useState(false);
  const [storageSaveError, setStorageSaveError] = useState("");
  const [storageSaving, setStorageSaving] = useState(false);
  const [benchmarkDirty, setBenchmarkDirty] = useState(false);
  const [benchmarkSaveError, setBenchmarkSaveError] = useState("");
  const [benchmarkSaving, setBenchmarkSaving] = useState(false);

  const sections = useMemo(() => snapshot?.sections || [], [snapshot]);
  const activeSection = useMemo(
    () => sections.find((item) => item.id === activeSectionId) || sections[0] || null,
    [activeSectionId, sections],
  );

  async function handleSave(payload) {
    setSaving(true);
    setSaveError("");
    try {
      const next = await updateLlmSettings(payload);
      setSnapshot(next);
      setDirtyHint(false);
    } catch (error) {
      setSaveError(formatResearchApiError(error) || t("settings.page.saveError"));
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveIngestion(payload) {
    setIngestionSaving(true);
    setIngestionSaveError("");
    try {
      const next = await updateIngestionSettings(payload);
      setSnapshot(next);
      setIngestionDirty(false);
    } catch (error) {
      setIngestionSaveError(formatResearchApiError(error) || t("settings.ingestion.saveError"));
    } finally {
      setIngestionSaving(false);
    }
  }

  async function handleSaveGeneral(payload) {
    setGeneralSaving(true);
    setGeneralSaveError("");
    try {
      const next = await updateGeneralSettings(payload);
      setSnapshot(next);
      setGeneralDirty(false);
    } catch (error) {
      setGeneralSaveError(formatResearchApiError(error) || t("settings.general.openalex.saveError"));
    } finally {
      setGeneralSaving(false);
    }
  }

  async function handleSaveStorage(payload) {
    setStorageSaving(true);
    setStorageSaveError("");
    try {
      const next = await updateStorageSettings(payload);
      setSnapshot(next);
      setStorageDirty(false);
    } catch (error) {
      setStorageSaveError(formatResearchApiError(error) || t("settings.storage.saveError"));
    } finally {
      setStorageSaving(false);
    }
  }

  async function handleSaveBenchmark(payload) {
    setBenchmarkSaving(true);
    setBenchmarkSaveError("");
    try {
      const next = await updateBenchmarkSettings(payload);
      setSnapshot(next);
      setBenchmarkDirty(false);
    } catch (error) {
      setBenchmarkSaveError(formatResearchApiError(error) || t("settings.benchmark.saveError"));
      throw error;
    } finally {
      setBenchmarkSaving(false);
    }
  }

  async function handleDeleteSecret() {
    setSaving(true);
    setSaveError("");
    try {
      const next = await deleteLlmSecret();
      setSnapshot(next);
    } catch (error) {
      setSaveError(formatResearchApiError(error) || t("settings.page.removeKeyError"));
    } finally {
      setSaving(false);
    }
  }

  async function handleTest(payload) {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testLlmConnection(payload);
      setTestResult(result);
    } catch (error) {
      setTestResult({
        status: "error",
        error_kind: "request_failed",
        message: formatResearchApiError(error) || t("settings.page.connectionFailed"),
      });
    } finally {
      setTesting(false);
    }
  }

  function renderSection() {
    if (!activeSection) return null;
    if (activeSection.id === "general") {
      return (
        <GeneralSettingsPanel
          general={snapshot?.general}
          saving={generalSaving}
          saveError={generalSaveError}
          onSave={handleSaveGeneral}
          onDirtyChange={setGeneralDirty}
        />
      );
    }
    if (activeSection.id === "llm") {
      return (
        <LlmSettingsPanel
          llm={snapshot?.llm}
          schema={schema}
          saving={saving}
          testing={testing}
          saveError={saveError}
          testResult={testResult}
          onSave={handleSave}
          onDeleteSecret={handleDeleteSecret}
          onTestSaved={() => handleTest({ use_saved_secret: true })}
          onTestDraft={(payload) => handleTest(payload)}
          onDirtyChange={setDirtyHint}
        />
      );
    }
    if (activeSection.id === "ingestion") {
      return (
        <IngestionSettingsPanel
          ingestion={snapshot?.ingestion}
          saving={ingestionSaving}
          saveError={ingestionSaveError}
          onSave={handleSaveIngestion}
          onDirtyChange={setIngestionDirty}
        />
      );
    }
    if (activeSection.id === "storage") {
      return (
        <StorageSettingsPanel
          storage={snapshot?.storage}
          saving={storageSaving}
          saveError={storageSaveError}
          onSave={handleSaveStorage}
          onDirtyChange={setStorageDirty}
        />
      );
    }
    if (activeSection.id === "diagnostics") {
      return <DiagnosticsSettingsPanel diagnostics={snapshot?.diagnostics} />;
    }
    if (activeSection.id === "security") {
      return <SecuritySettingsPanel security={snapshot?.security} />;
    }
    if (activeSection.id === "benchmark") {
      return (
        <BenchmarkSettingsPanel
          benchmark={snapshot?.benchmark}
          saving={benchmarkSaving}
          saveError={benchmarkSaveError}
          onSave={handleSaveBenchmark}
          onDirtyChange={setBenchmarkDirty}
        />
      );
    }
    const labelKey = `settings.snapshot.${activeSection.id}.label`;
    const descKey = `settings.snapshot.${activeSection.id}.description`;
    const title = t(labelKey) !== labelKey ? t(labelKey) : activeSection.label;
    const description = t(descKey) !== descKey ? t(descKey) : activeSection.description;
    return <PlaceholderSettingsSection title={title} description={description} />;
  }

  if (loading) {
    return (
      <Box sx={{ padding: 3 }}>
        <Typography sx={{ fontSize: "0.875rem", color: tk.text.muted }}>{t("settings.page.loading")}</Typography>
      </Box>
    );
  }

  if (loadError) {
    return (
      <Box sx={{ padding: 3 }}>
        <Alert
          severity="error"
          sx={{
            backgroundColor: tk.control.outlinedBg,
            border: `1px solid ${tk.border.default}`,
            color: tk.text.primary,
            "& .MuiAlert-icon": { color: tk.state.dangerFg },
          }}
        >
          <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary }}>{loadError}</Typography>
        </Alert>
      </Box>
    );
  }

  return (
    <SettingsLayout
      sections={sections}
      activeSectionId={activeSectionId}
      onSelectSection={setActiveSectionId}
      heading={t("settings.page.heading")}
      subheading={`${t("settings.page.subheadingPrefix")}${schema ? t("settings.page.subheadingSchema", { version: schema.version }) : ""}`}
      dirty={dirtyHint || ingestionDirty || generalDirty || storageDirty || benchmarkDirty}
    >
      <Box sx={{ mb: 2, display: "flex", flexWrap: "wrap", gap: 0.75 }}>
        <CursorIconAction component={Link} to="/admin" title={t("settings.page.adminHub")}>
          <AdminPanelSettingsOutlinedIcon sx={{ fontSize: "1.1rem" }} />
        </CursorIconAction>
        <CursorIconAction component={Link} to="/" title={t("settings.page.home")}>
          <HomeOutlinedIcon sx={{ fontSize: "1.1rem" }} />
        </CursorIconAction>
      </Box>
      {renderSection()}
    </SettingsLayout>
  );
}
