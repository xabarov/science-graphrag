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
    chat_base_url: "",
    embeddings_mode: "openrouter",
    embeddings_model: "",
    temperature: 0,
    status: {
      configured: true,
      has_saved_secret: true,
      has_saved_chat_secret: false,
      has_saved_embeddings_secret: false,
      has_saved_vision_secret: false,
      secret_source: "saved",
      masked_key: "sk-***",
    },
    vl_model: "",
    vl_base_url: "",
    effective: {
      resolved_timeout_seconds: 120,
      resolved_model: "openai/gpt-4o-mini",
      resolved_base_url: "https://openrouter.ai/api/v1",
      resolved_chat_base_url: "https://openrouter.ai/api/v1",
      resolved_vl_model: "qwen/qwen3-vl-235b-a22b-instruct",
      resolved_vl_base_url: "https://openrouter.ai/api/v1",
      resolved_embeddings_base_url: "https://openrouter.ai/api/v1",
    },
    tasks: {
      extraction: {
        base_url: "https://openrouter.ai/api/v1",
        model: "openai/gpt-4o-mini",
        temperature: 0,
        timeout_seconds: 120,
        api_key: { source: "saved", masked: "sk-***" },
      },
      chat: {
        base_url: "https://openrouter.ai/api/v1",
        model: "openai/gpt-4o-mini",
        temperature: 0,
        timeout_seconds: 120,
        inherits_extraction_model: true,
        api_key: { source: "saved" },
      },
      vision: {
        base_url: "https://openrouter.ai/api/v1",
        model: "qwen/qwen3-vl-235b-a22b-instruct",
        temperature: 0,
        timeout_seconds: 300,
        api_key: { source: "inherited", masked: "sk-***" },
      },
      embeddings: {
        mode: "openrouter",
        base_url: "https://openrouter.ai/api/v1",
        model: "baai/bge-m3",
        model_label: "baai/bge-m3",
        timeout_seconds: 60,
      },
    },
    diagnostics: {},
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

  it("renders extraction task card heading", () => {
    renderPanel();
    expect(screen.getByText("Extraction (text / structure)")).toBeTruthy();
  });

  it("renders embeddings HTTP controls", () => {
    renderPanel();
    expect(screen.getByLabelText("Embeddings model")).toBeTruthy();
    expect(screen.queryByText(/Mode:/i)).toBeNull();
  });

  it("renders provider preset controls", () => {
    renderPanel();
    expect(screen.getByText("Provider preset")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Ollama local" })).toBeTruthy();
  });

  it("applies Ollama preset into form fields and enables save", () => {
    renderPanel();
    const saveButton = screen.getByRole("button", { name: /^Save/i });
    expect(saveButton.disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Ollama local" }));
    const baseUrlFields = screen.getAllByDisplayValue("http://localhost:11434/v1");
    expect(baseUrlFields.length).toBeGreaterThanOrEqual(4);
    expect(screen.getAllByDisplayValue("llama3.2").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByDisplayValue("all-minilm")).toBeTruthy();
    expect(screen.getByDisplayValue("llava")).toBeTruthy();
    expect(screen.getByText(/Ollama endpoint detected/i)).toBeTruthy();
    expect(saveButton.disabled).toBe(false);
  });
});
