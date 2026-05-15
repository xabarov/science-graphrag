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
      resolved_external_research_sources: { crossref: true, arxiv: true, unpaywall: true, openalex: true },
      resolved_pdf_reading_mode: "ask",
      resolved_agent_unpaywall_oa_tool_enabled: true,
      resolved_agent_supervisor_max_rounds: 10,
      resolved_agent_external_http_timeout_seconds: 25,
      resolved_agent_external_max_calls_per_turn: 8,
      resolved_agent_external_max_source_cards: 24,
    },
    sources: [
      { id: "crossref", label: "Crossref", tier: "stable", status: "ok", last_test: null, last_error: null },
    ],
    integrations: { mcp_tools_enabled: false, mcp_http_base_url_configured: false, mcp_server_denylist_count: 0 },
    credentials: { research_contact_email_status: "configured" },
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
    });
  });

  it("localizes research contact email status in credentials line", () => {
    renderPanel(makeAgentTools());
    expect(
      screen.getByText("Research contact email (mailto / polite pool): Configured"),
    ).toBeTruthy();
  });
});
