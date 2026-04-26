import React from "react";
import { Link } from "react-router-dom";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import LightbulbOutlinedIcon from "@mui/icons-material/LightbulbOutlined";
import QuestionAnswerIcon from "@mui/icons-material/QuestionAnswer";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";

import { CopyIdButton, CursorIconAction } from "../../components/common/index.js";
import PageHeader from "../../components/layout/PageHeader.jsx";
import PageActionToolbar from "../../components/layout/PageActionToolbar.jsx";
import WorkIdGlossaryHint from "../../components/layout/WorkIdGlossaryHint.jsx";
import { workAskUrl, workGraphUrl } from "./workspacePageUrls.js";

/**
 * @param {{ t: (key: string, vars?: Record<string, string>) => string, vm: Record<string, unknown> }} props
 */
export default function WorkspaceHero({ t, vm }) {
  const description =
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
              <span>{vm.papers.get(vm.selectedWorkId)?.title || t("workspace.paper.noTitle")}</span>
            </>
          ) : null}
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
    );

  const actionGroups =
    vm.workspaceMeta.id
      ? [
          [
            <CursorIconAction
              key="wg"
              component={Link}
              to={workGraphUrl("", vm.workspaceMeta.id)}
              title={t("workspace.tooltip.workspaceGraph")}
            >
              <AccountTreeIcon sx={{ fontSize: "1.1rem" }} />
            </CursorIconAction>,
            <CursorIconAction
              key="ask"
              component={Link}
              to={workAskUrl("", vm.workspaceMeta.id)}
              title={t("workspace.tooltip.askWorkspace")}
            >
              <QuestionAnswerIcon sx={{ fontSize: "1.1rem" }} />
            </CursorIconAction>,
          ],
          [
            <CursorIconAction key="sum" title={t("workspace.tooltip.summarize")} onClick={vm.handleSummarizeWorkspace} busy={vm.summaryBusy}>
              <AutoAwesomeIcon sx={{ fontSize: "1.1rem" }} />
            </CursorIconAction>,
            ...(vm.canUseIdeaAssist
              ? [
                  <CursorIconAction
                    key="hyp"
                    title={t("workspace.tooltip.generateHypotheses")}
                    onClick={vm.handleGenerateHypotheses}
                    busy={vm.ideaBusy}
                  >
                    <LightbulbOutlinedIcon sx={{ fontSize: "1.1rem" }} />
                  </CursorIconAction>,
                ]
              : []),
          ],
        ]
      : [];

  return (
    <Box
      sx={{
        mb: 2,
        p: { xs: 1.25, md: 1.5 },
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "#1a1a1a",
      }}
    >
      <PageHeader
        compact
        eyebrow={vm.workspaceMeta.id ? "" : t("workspace.header.eyebrow")}
        title={vm.workspaceMeta.name || t("workspace.header.titleFallback")}
        description={description}
        actions={null}
      />
      {vm.workspaceMeta.id ? (
        <PageActionToolbar
          groups={actionGroups}
          tail={
            <CopyIdButton
              id={vm.workspaceMeta.id}
              tooltipCopy={t("workspace.tooltip.copyWorkspaceId")}
              tooltipCopied={t("workspace.tooltip.copied")}
            />
          }
        />
      ) : null}
    </Box>
  );
}
