/** @vitest-environment jsdom */
import { ThemeProvider } from "@mui/material/styles";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import React from "react";
import { MemoryRouter } from "react-router-dom";

import WorkspaceContextStrip from "./WorkspaceContextStrip.jsx";

import { buildAppTheme } from "../../theme/buildAppTheme.js";

const theme = buildAppTheme("dark");

function t(key) {
  const map = {
    "workspace.header.titleFallback": "WS",
    "workspace.header.paperCountOne": "1 paper",
    "workspace.tooltip.workspaceGraph": "Graph",
    "workspace.tooltip.chatWorkspace": "Chat",
    "workspace.tooltip.summarize": "Sum",
    "workspace.strip.ingestProgressTip": "Tip",
    "workspace.strip.ingestProgressTwoScalesHint": "Two scales hint",
    "workspace.strip.ingestPhase.preparing_search": "Search layer",
    "workspace.strip.ingestStage.embed": "Embedding chunks",
    "workspace.strip.addMenuAria": "Add",
    "workspace.strip.addMenuTooltip": "Add tip",
    "workspace.tooltip.copyWorkspaceId": "Copy",
    "workspace.tooltip.copied": "Copied",
  };
  return map[key] || key;
}

describe("WorkspaceContextStrip", () => {
  it("shows humanized ingest stage secondary line when job is running", () => {
    const vm = {
      workspaceLoading: false,
      workspaceMeta: { id: "ws-1", name: "Lab" },
      effectiveWorkIds: ["w1"],
      papers: new Map(),
      selectedWorkId: null,
      graphStats: null,
      uploadBusy: false,
      ingestJobId: "j1",
      ingestJob: {
        status: "running",
        progress_pct: 0.42,
        stages: [{ stage: "embed", status: "running" }],
      },
      ingestErr: null,
      summaryBusy: false,
      ideaBusy: false,
      canUseIdeaAssist: false,
      handleSummarizeWorkspace: () => {},
      handleGenerateHypotheses: () => {},
      handleUploadDocument: () => {},
      handleUploadBatch: () => {},
      handleAddWork: () => {},
      addWorkInput: "",
      setAddWorkInput: () => {},
      addBusy: false,
    };

    render(
      <MemoryRouter>
        <ThemeProvider theme={theme}>
          <WorkspaceContextStrip t={t} vm={vm} />
        </ThemeProvider>
      </MemoryRouter>,
    );

    expect(screen.getByText("Embedding chunks")).toBeTruthy();
    expect(screen.getByText("Search layer")).toBeTruthy();
  });
});
