import React, { useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import LlmSettingsPanel from "./SettingsPage/LlmSettingsPanel.jsx";
import SettingsLayout from "./SettingsPage/SettingsLayout.jsx";
import {
  deleteLlmSecret,
  getSettingsSchema,
  getSettingsSnapshot,
  testLlmConnection,
  updateLlmSettings,
} from "./SettingsPage/settingsApi.js";

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
        setLoadError(error?.response?.data?.detail || error?.message || "Failed to load settings.");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, []);

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
      setSaveError(error?.response?.data?.detail || error?.message || "Failed to save settings.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteSecret() {
    setSaving(true);
    setSaveError("");
    try {
      const next = await deleteLlmSecret();
      setSnapshot(next);
    } catch (error) {
      setSaveError(error?.response?.data?.detail || error?.message || "Failed to remove API key.");
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
        message: error?.response?.data?.detail || error?.message || "Connection test failed.",
      });
    } finally {
      setTesting(false);
    }
  }

  function renderSection() {
    if (!activeSection) return null;
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
    return <PlaceholderSection title={activeSection.label} description={activeSection.description} />;
  }

  if (loading) {
    return (
      <Box sx={{ padding: 3 }}>
        <Typography sx={{ fontSize: "0.875rem", color: "rgba(255,255,255,0.65)" }}>
          Loading settings...
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
      heading="Settings"
      subheading={`Secure runtime configuration for providers, extraction defaults, and future system sections.${schema ? ` Schema v${schema.version}` : ""}`}
      dirty={dirtyHint}
    >
      {renderSection()}
    </SettingsLayout>
  );
}
