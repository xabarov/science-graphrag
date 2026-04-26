import React from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";

import { CursorSmallButton } from "../../components/common/index.js";
import PageHeader from "../../components/layout/PageHeader.jsx";
import WorkIdGlossaryHint from "../../components/layout/WorkIdGlossaryHint.jsx";
import { workAskUrl, workGraphUrl } from "./workspacePageUrls.js";

/**
 * @param {{ t: (key: string, vars?: Record<string, string>) => string, vm: Record<string, unknown> }} props
 */
export default function WorkspaceHero({ t, vm }) {
  return (
    <Box
      sx={{
        mb: 2,
        p: { xs: 1.5, md: 2 },
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "#1a1a1a",
        minHeight: { lg: 120 },
      }}
    >
      <PageHeader
        eyebrow={t("workspace.header.eyebrow")}
        title={vm.workspaceMeta.name || t("workspace.header.titleFallback")}
        description={
          vm.workspaceLoading ? (
            <Box sx={{ display: "inline-flex", alignItems: "center", gap: 1 }}>
              <CircularProgress size={18} sx={{ color: "rgba(129,140,248,0.9)" }} />
              <span>{t("workspace.header.loadingWs")}</span>
            </Box>
          ) : vm.workspaceMeta.id ? (
            <>
              <span style={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem" }}>
                {vm.effectiveWorkIds.length === 1
                  ? t("workspace.header.paperCountOne", { count: String(vm.effectiveWorkIds.length) })
                  : t("workspace.header.paperCountMany", { count: String(vm.effectiveWorkIds.length) })}
                {vm.effectiveWorkIds.length > 1 && vm.selectedWorkId ? (
                  <>
                    <br />
                    <span style={{ color: "rgba(129,140,248,0.95)" }}>{t("workspace.header.focusedPaper")} </span>
                    <span>{vm.papers.get(vm.selectedWorkId)?.title || vm.selectedWorkId}</span>
                  </>
                ) : null}
              </span>
              <br />
              <span style={{ color: "rgba(255,255,255,0.38)", fontFamily: "monospace", fontSize: "0.72rem" }}>
                {vm.workspaceMeta.id}
              </span>
              {vm.graphStats && typeof vm.graphStats === "object" ? (
                <>
                  <br />
                  <span style={{ color: "rgba(255,255,255,0.42)", fontSize: "0.75rem" }}>
                    {t("workspace.header.graphStatsLine", {
                      works: String(vm.graphStats.works_count ?? "—"),
                      authors: String(vm.graphStats.authors_count ?? "—"),
                      internal: String(vm.graphStats.internal_citations ?? "—"),
                      external: String(vm.graphStats.external_citations ?? "—"),
                    })}
                  </span>
                </>
              ) : null}
            </>
          ) : (
            <WorkIdGlossaryHint variant="workspace" />
          )
        }
        actions={
          vm.workspaceMeta.id ? (
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
              <CursorSmallButton component={Link} to={workGraphUrl("", vm.workspaceMeta.id)} sx={{ textDecoration: "none" }}>
                {t("workspace.header.workspaceGraph")}
              </CursorSmallButton>
              <CursorSmallButton component={Link} to={workAskUrl("", vm.workspaceMeta.id)} sx={{ textDecoration: "none" }}>
                {t("workspace.actions.askWorkspace")}
              </CursorSmallButton>
              <CursorSmallButton onClick={vm.handleSummarizeWorkspace} disabled={vm.summaryBusy}>
                {vm.summaryBusy ? t("workspace.header.summarizing") : t("workspace.header.summarizeAction")}
              </CursorSmallButton>
              {vm.canUseIdeaAssist ? (
                <CursorSmallButton onClick={vm.handleGenerateHypotheses} disabled={vm.ideaBusy}>
                  {vm.ideaBusy ? t("workspace.header.generatingHypotheses") : t("workspace.header.generateHypotheses")}
                </CursorSmallButton>
              ) : null}
            </Box>
          ) : null
        }
      />
    </Box>
  );
}
