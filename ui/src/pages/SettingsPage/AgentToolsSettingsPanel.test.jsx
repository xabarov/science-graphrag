/** @vitest-environment jsdom */
import React from "react";
import { ThemeProvider } from "@mui/material/styles";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../../i18n/I18nContext.jsx";
import { buildAppTheme } from "../../theme/buildAppTheme.js";

import AgentToolsSettingsPanel from "./AgentToolsSettingsPanel.jsx";

const theme = buildAppTheme("dark");

afterEach(() => {
  cleanup();
});

function makeAgentTools() {
  return {
    effective: {
      resolved_external_research_default_enabled: true,
      resolved_external_research_sources: {
        crossref: true,
        arxiv: true,
        unpaywall: true,
        openalex: true,
        semantic_scholar: true,
      },
      resolved_pdf_reading_mode: "ask",
      resolved_agent_pdf_read_backend_mode: "hybrid",
      resolved_agent_unpaywall_oa_tool_enabled: true,
      resolved_agent_supervisor_max_rounds: 10,
      resolved_agent_external_http_timeout_seconds: 25,
      resolved_agent_external_max_calls_per_turn: 8,
      resolved_agent_external_max_source_cards: 24,
      resolved_agent_pdf_read_tool_enabled: true,
      resolved_agent_pdf_read_max_bytes: 8000000,
      resolved_agent_pdf_read_max_pages: 30,
      resolved_agent_pdf_read_cache_ttl_seconds: 300,
      resolved_agent_pdf_read_cache_max_entries: 256,
      resolved_agent_pdf_read_durable_cache_enabled: true,
      resolved_agent_mcp_request_timeout_seconds: 15,
      resolved_agent_mcp_server_denylist: ["evil"],
    },
    sources: [
      { id: "crossref", label: "Crossref", tier: "stable", status: "ok", last_test: null, last_error: null },
    ],
    integrations: {
      mcp_tools_enabled: false,
      mcp_http_base_url_configured: false,
      mcp_operator_state: "disabled",
      mcp_request_timeout_seconds: 15,
      mcp_server_denylist_count: 0,
      mcp_server_denylist_preview: [],
      mcp_auth_model: "delegation_required",
      mcp_adapter_url_source: "environment",
    },
    credentials: {
      research_contact_email_status: "configured",
      semantic_scholar_api_key_status: "not_configured",
      pdf_read_durable_cache: "disabled_no_redis",
    },
  };
}

function renderPanel(agentTools, onSave = vi.fn(), onDirty = vi.fn()) {
  return render(
    <ThemeProvider theme={theme}>
      <I18nProvider>
        <AgentToolsSettingsPanel
          agentTools={agentTools}
          saving={false}
          saveError=""
          onSave={onSave}
          onDirtyChange={onDirty}
        />
      </I18nProvider>
    </ThemeProvider>,
  );
}

describe("AgentToolsSettingsPanel", () => {
  it("renders source diagnostics and not the generic placeholder", () => {
    renderPanel(makeAgentTools());
    expect(screen.getAllByText("Crossref").length).toBeGreaterThan(0);
    expect(screen.getByText("web_search / web_fetch")).toBeTruthy();
    expect(screen.getByText(/^Agent tools$/)).toBeTruthy();
  });

  it("marks dirty and submits allowlisted payload", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const onDirty = vi.fn();
    renderPanel(makeAgentTools(), onSave, onDirty);
    fireEvent.click(screen.getAllByRole("switch")[0]);
    await waitFor(() => expect(onDirty).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: /Save settings|Сохранить/i }));
    expect(onSave).toHaveBeenCalledTimes(1);
    const payload = onSave.mock.calls[0][0];
    expect(payload.external_research_default_enabled).toBe(false);
    expect(payload.external_research_sources).toMatchObject({
      crossref: true,
      arxiv: true,
      unpaywall: true,
      openalex: true,
      semantic_scholar: true,
    });
    expect(payload.agent_pdf_read_durable_cache_enabled).toBe(true);
    expect(payload.agent_pdf_read_backend_mode).toBe("hybrid");
  });

  it("changes PDF extraction backend and persists on save", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    renderPanel(makeAgentTools(), onSave);
    const backendSelect = screen.getByRole("combobox", { name: /PDF extraction backend|Бэкенд извлечения текста из PDF/i });
    fireEvent.mouseDown(backendSelect);
    const opts = await screen.findAllByRole("option", { name: /pypdf/i });
    const pypdf = opts.find((el) => el.getAttribute("data-value") === "pypdf");
    expect(pypdf).toBeTruthy();
    fireEvent.click(pypdf);
    fireEvent.click(screen.getByRole("button", { name: /Save settings|Сохранить/i }));
    await waitFor(() => expect(onSave).toHaveBeenCalled());
    const payload = onSave.mock.calls[0][0];
    expect(payload.agent_pdf_read_backend_mode).toBe("pypdf");
  });

  it("localizes research contact email status in credentials line", () => {
    renderPanel(makeAgentTools());
    expect(
      screen.getByText("Research contact email (mailto / polite pool): Configured"),
    ).toBeTruthy();
  });

  it("shows MCP operator state chip and advanced section", () => {
    renderPanel(makeAgentTools());
    expect(screen.getByText("Disabled")).toBeTruthy();
    expect(screen.getByText(/MCP advanced/i)).toBeTruthy();
  });

  it("seeds denylist from effective snapshot and submits MCP knobs on save", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    renderPanel(makeAgentTools(), onSave);
    fireEvent.click(screen.getByRole("button", { name: /MCP advanced|MCP — расширенные/i }));
    expect(screen.getByDisplayValue("evil")).toBeTruthy();
    const timeoutField = screen.getByRole("spinbutton", {
      name: /MCP request timeout|Таймаут MCP/i,
    });
    fireEvent.change(timeoutField, { target: { value: "30" } });
    fireEvent.click(screen.getByRole("button", { name: /Save settings|Сохранить/i }));
    await waitFor(() => expect(onSave).toHaveBeenCalled());
    const payload = onSave.mock.calls[0][0];
    expect(payload.agent_mcp_request_timeout_seconds).toBe(30);
    expect(payload.agent_mcp_server_denylist).toEqual(["evil"]);
  });
});
