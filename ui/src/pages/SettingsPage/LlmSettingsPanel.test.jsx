/** @vitest-environment jsdom */
import React from "react";
import { ThemeProvider } from "@mui/material/styles";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../../i18n/I18nContext.jsx";
import { buildAppTheme } from "../../theme/buildAppTheme.js";

import LlmSettingsPanel from "./LlmSettingsPanel.jsx";

const theme = buildAppTheme("dark");

afterEach(() => {
  cleanup();
});

const distSchemaFields = [
  { id: "llm_distributed_quota_enabled", group: "llm_distributed_quota" },
  { id: "llm_distributed_quota_key_prefix", group: "llm_distributed_quota" },
  { id: "llm_distributed_quota_acquire_timeout_seconds", group: "llm_distributed_quota" },
  { id: "llm_distributed_quota_lease_seconds", group: "llm_distributed_quota" },
];

function makeLlm(overrides = {}) {
  return {
    base_url: "https://openrouter.ai/api/v1",
    model: "openai/gpt-4o-mini",
    chat_model: "",
    temperature: 0,
    status: {
      configured: true,
      has_saved_secret: true,
      has_saved_vision_secret: false,
      secret_source: "server_managed",
      masked_key: "sk-***",
      vl_api_key_explicit_env: false,
    },
    vl_model: "",
    vl_base_url: "",
    effective: {
      resolved_timeout_seconds: 120,
      resolved_model: "openai/gpt-4o-mini",
      resolved_base_url: "https://openrouter.ai/api/v1",
      resolved_vl_model: "qwen/qwen3-vl-235b-a22b-instruct",
      resolved_vl_base_url: "https://openrouter.ai/api/v1",
    },
    tasks: {
      extraction: { model: "openai/gpt-4o-mini", api_key: { source: "server_managed", masked: "sk-***" } },
      chat: { model: "openai/gpt-4o-mini", inherits_extraction_model: true, api_key: { source: "server_managed" } },
      vision: {
        model: "qwen/qwen3-vl-235b-a22b-instruct",
        api_key: { source: "inherited", masked: "sk-***" },
      },
      embeddings: { mode: "hash_deterministic", model_label: "hash-deterministic" },
    },
    diagnostics: { operator_env_variables: ["SCIENCE_GRAPHRAG_API_KEY"], notes: "op" },
    advanced_controls: {
      llm_distributed_quota_enabled: { effective: false, persisted: false },
      llm_distributed_quota_key_prefix: { effective: "science_graphrag:llm_quota:v1", persisted: null },
      llm_distributed_quota_acquire_timeout_seconds: { effective: 60, persisted: null },
      llm_distributed_quota_lease_seconds: { effective: 420, persisted: null },
    },
    ...overrides,
  };
}

function renderPanel(llm = makeLlm()) {
  const schema = { sections: [{ id: "llm", fields: distSchemaFields }] };
  return render(
    <ThemeProvider theme={theme}>
      <I18nProvider>
        <LlmSettingsPanel
          llm={llm}
          schema={schema}
          saving={false}
          testing={false}
          saveError={null}
          testResult={null}
          onSave={vi.fn()}
          onDeleteSecret={vi.fn()}
          onDeleteVisionSecret={vi.fn()}
          onTestSaved={vi.fn()}
          onTestDraft={vi.fn()}
          onDirtyChange={vi.fn()}
        />
      </I18nProvider>
    </ThemeProvider>,
  );
}

describe("LlmSettingsPanel distributed quota UX", () => {
  it("shows operator blurb when advanced section is expanded", () => {
    renderPanel();
    fireEvent.click(screen.getByText(/Show advanced/i));
    expect(screen.getByText(/Requires a reachable Redis/i)).toBeTruthy();
  });

  it("does not block save when distributed quota key prefix is non-numeric", () => {
    renderPanel();
    expect(screen.queryByText(/Enter valid numbers for all advanced numeric fields/i)).toBeNull();
    expect(screen.queryByText(/Advanced numeric fields cannot be empty/i)).toBeNull();
  });

  it("renders task overrides heading", () => {
    renderPanel();
    expect(screen.getByText(/Models by task/i)).toBeTruthy();
  });
});
