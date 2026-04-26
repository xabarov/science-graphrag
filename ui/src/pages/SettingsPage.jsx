import React, { useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { Link } from "react-router-dom";

import AdminPanelSettingsOutlinedIcon from "@mui/icons-material/AdminPanelSettingsOutlined";
import HomeOutlinedIcon from "@mui/icons-material/HomeOutlined";

import { CursorIconAction } from "../components/common/index.js";
import DiagnosticsSettingsPanel from "./SettingsPage/DiagnosticsSettingsPanel.jsx";
import IngestionSettingsPanel from "./SettingsPage/IngestionSettingsPanel.jsx";
import GeneralSettingsPanel from "./SettingsPage/GeneralSettingsPanel.jsx";
import LlmSettingsPanel from "./SettingsPage/LlmSettingsPanel.jsx";
import SecuritySettingsPanel from "./SettingsPage/SecuritySettingsPanel.jsx";
import SettingsLayout from "./SettingsPage/SettingsLayout.jsx";
import {
  deleteLlmSecret,
  getSettingsSchema,
  getSettingsSnapshot,
  testLlmConnection,
  updateIngestionSettings,
  updateLlmSettings,
} from "./SettingsPage/settingsApi.js";
import { formatResearchApiError } from "../services/researchApi.js";
import { useI18n } from "../i18n/I18nContext.jsx";

function PlaceholderSection({ title, description }) {
  return (
    <Box
      sx={{
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "#1a1a1a",
        borderRadius: 1.5,
        padding: 2.5,
      }}
    >
      <Typography sx={{ fontSize: "0.875rem", fontWeight: 600 }}>{title}</Typography>
      <Typography sx={{ marginTop: 1, fontSize: "0.8125rem", color: "rgba(255,255,255,0.58)", lineHeight: 1.6 }}>
        {description}
      </Typography>
    </Box>
  );
}

export default function SettingsPage() {
  const { t } = useI18n();
  const [snapshot, setSnapshot] = useState(null);
  const [schema, setSchema] = useState(null);
  const [activeSectionId, setActiveSectionId] = useState("llm");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [dirtyHint, setDirtyHint] = useState(false);
  const [ingestionDirty, setIngestionDirty] = useState(false);
  const [ingestionSaveError, setIngestionSaveError] = useState("");
  const [ingestionSaving, setIngestionSaving] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true);
      setLoadError("");
      try {
        const [nextSchema, nextSnapshot] = await Promise.all([
          getSettingsSchema(),
          getSettingsSnapshot(),
        ]);
        if (!mounted) return;
        setSchema(nextSchema);
        setSnapshot(nextSnapshot);
        const active = nextSnapshot.sections.some((item) => item.id === "llm")
          ? "llm"
          : nextSnapshot.sections[0]?.id || "llm";
        setActiveSectionId(active);
      } catch (error) {
        if (!mounted) return;
        setLoadError(formatResearchApiError(error) || t("settings.page.loadError"));
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, [t]);

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
      return <GeneralSettingsPanel />;
    }
    if (activeSection.id === "llm") {
      return (
        <LlmSettingsPanel
          llm={snapshot?.llm}
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
    if (activeSection.id === "diagnostics") {
      return <DiagnosticsSettingsPanel diagnostics={snapshot?.diagnostics} />;
    }
    if (activeSection.id === "security") {
      return <SecuritySettingsPanel security={snapshot?.security} />;
    }
    const labelKey = `settings.snapshot.${activeSection.id}.label`;
    const descKey = `settings.snapshot.${activeSection.id}.description`;
    const title = t(labelKey) !== labelKey ? t(labelKey) : activeSection.label;
    const description = t(descKey) !== descKey ? t(descKey) : activeSection.description;
    return <PlaceholderSection title={title} description={description} />;
  }

  if (loading) {
    return (
      <Box sx={{ padding: 3 }}>
        <Typography sx={{ fontSize: "0.875rem", color: "rgba(255,255,255,0.65)" }}>
          {t("settings.page.loading")}
        </Typography>
      </Box>
    );
  }

  if (loadError) {
    return (
      <Box sx={{ padding: 3 }}>
        <Alert
          severity="error"
          sx={{
            backgroundColor: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          <Typography sx={{ fontSize: "0.8125rem" }}>{loadError}</Typography>
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
      dirty={dirtyHint || ingestionDirty}
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
