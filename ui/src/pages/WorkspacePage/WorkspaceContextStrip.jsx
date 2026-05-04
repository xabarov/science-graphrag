import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import LightbulbOutlinedIcon from "@mui/icons-material/LightbulbOutlined";
import QuestionAnswerIcon from "@mui/icons-material/QuestionAnswer";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CopyIdButton, CursorIconAction } from "../../components/common/index.js";
import {
  INGEST_PHASE_KEYS,
  fallbackHumanIngestStageLabel,
  ingestPhaseFromJob,
  ingestStageIdFromRow,
  ingestStageMessageKey,
  pickActiveIngestStage,
} from "../../components/ingestion/ingestStripModel.js";
import WorkIdGlossaryHint from "../../components/layout/WorkIdGlossaryHint.jsx";
import { workChatUrl, workGraphUrl } from "./workspacePageUrls.js";
import WorkspaceIngestMenu from "./WorkspaceIngestMenu.jsx";
import WorkspaceIngestProgressStrip from "./WorkspaceIngestProgressStrip.jsx";
import WorkspaceStripGraphStats from "./WorkspaceStripGraphStats.jsx";

/**
 * Single compact command strip for workspace overview (Cursor-like).
 * Workspace selection lives in shell only — no duplicate WorkspaceSwitcher here.
 *
 * @param {{ t: (key: string, vars?: Record<string, string>) => string, vm: Record<string, unknown> }} props
 */
export default function WorkspaceContextStrip({ t, vm }) {
  const tk = useTheme().appTokens;
  const gs = vm.graphStats && typeof vm.graphStats === "object" ? vm.graphStats : null;
  const hasWs = Boolean(vm.workspaceMeta?.id);
  const multiPapers = vm.effectiveWorkIds?.length > 1;
  const focusedTitle = vm.selectedWorkId ? vm.papers?.get?.(vm.selectedWorkId)?.title : null;

  const actionGroups =
    hasWs
      ? [
          <CursorIconAction
            key="wg"
            component={Link}
            to={workGraphUrl("", vm.workspaceMeta.id)}
            title={t("workspace.tooltip.workspaceGraph")}
          >
            <AccountTreeIcon sx={{ fontSize: "1.05rem" }} />
          </CursorIconAction>,
          <CursorIconAction
            key="ask"
            component={Link}
            to={workChatUrl("", vm.workspaceMeta.id)}
            title={t("workspace.tooltip.chatWorkspace")}
          >
            <QuestionAnswerIcon sx={{ fontSize: "1.05rem" }} />
          </CursorIconAction>,
          <CursorIconAction key="sum" title={t("workspace.tooltip.summarize")} onClick={vm.handleSummarizeWorkspace} busy={vm.summaryBusy}>
            <AutoAwesomeIcon sx={{ fontSize: "1.05rem" }} />
          </CursorIconAction>,
          ...(vm.canUseIdeaAssist
            ? [
                <CursorIconAction
                  key="hyp"
                  title={t("workspace.tooltip.generateHypotheses")}
                  onClick={vm.handleGenerateHypotheses}
                  busy={vm.ideaBusy}
                >
                  <LightbulbOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                </CursorIconAction>,
              ]
            : []),
        ]
      : [];

  const ingestBusy = Boolean(vm.uploadBusy || vm.ingestJobId);
  const batchPct =
    vm.ingestJob && String(vm.ingestJob.kind || "") === "batch_parent" && Array.isArray(vm.ingestJob.child_jobs)
      ? (() => {
          const jobs = vm.ingestJob.child_jobs;
          if (!jobs.length) return null;
          let sum = 0;
          let n = 0;
          for (const cj of jobs) {
            const tot = Number(cj.progress_total) || 0;
            const cur = Number(cj.progress_current) || 0;
            if (tot > 0) {
              sum += Math.min(100, (100 * cur) / tot);
              n += 1;
            } else if (typeof cj.progress_pct === "number" && Number.isFinite(cj.progress_pct)) {
              sum += Math.min(100, Math.max(0, cj.progress_pct * 100));
              n += 1;
            }
          }
          return n ? sum / n : null;
        })()
      : null;

  const parentServerPct =
    vm.ingestJob &&
    String(vm.ingestJob.kind || "") === "batch_parent" &&
    typeof vm.ingestJob.progress_pct === "number" &&
    Number.isFinite(vm.ingestJob.progress_pct)
      ? Math.min(100, Math.max(0, vm.ingestJob.progress_pct * 100))
      : null;

  const singlePct =
    vm.ingestJob &&
    String(vm.ingestJob.kind || "") !== "batch_parent" &&
    typeof vm.ingestJob.progress_pct === "number" &&
    Number.isFinite(vm.ingestJob.progress_pct)
      ? Math.min(100, Math.max(0, vm.ingestJob.progress_pct * 100))
      : null;

  const progressValue = parentServerPct != null ? parentServerPct : batchPct != null ? batchPct : singlePct;

  const ingestIndeterminate = useMemo(
    () => Boolean(vm.ingestJob && vm.ingestJob.progress_indeterminate),
    [vm.ingestJob],
  );

  const ingestStrip = useMemo(() => {
    if (!hasWs || !ingestBusy) return null;
    const job = vm.ingestJob && typeof vm.ingestJob === "object" ? vm.ingestJob : null;
    const stages = job && Array.isArray(job.stages) ? job.stages : [];
    const active = pickActiveIngestStage(stages);
    const stageId = ingestStageIdFromRow(active);
    const phaseKey = ingestPhaseFromJob(job, stageId);
    const statusLower = job ? String(job.status || "").toLowerCase() : "";
    const failed = statusLower === "failed";
    const starting = Boolean(vm.uploadBusy && !job);
    return { job, stageId, phaseKey, failed, starting };
  }, [hasWs, ingestBusy, vm.ingestJob, vm.uploadBusy]);

  const ingestStageSecondary = useMemo(() => {
    if (!ingestStrip?.stageId || ingestStrip.starting || ingestStrip.failed) return null;
    const key = ingestStageMessageKey(ingestStrip.stageId);
    const tx = t(key);
    return tx === key ? fallbackHumanIngestStageLabel(ingestStrip.stageId) : tx;
  }, [ingestStrip, t]);

  const ingestPhaseIdx = useMemo(() => {
    const pk = ingestStrip?.phaseKey || "preparing_document";
    const i = INGEST_PHASE_KEYS.indexOf(pk);
    return i === -1 ? 0 : i;
  }, [ingestStrip?.phaseKey]);

  return (
    <Box
      sx={{
        mb: 1.5,
        p: 1,
        borderRadius: 1,
        border: `1px solid ${tk.border.default}`,
        backgroundColor: tk.surface.subtle,
      }}
    >
      <Stack direction="row" flexWrap="wrap" alignItems="center" gap={1} useFlexGap sx={{ rowGap: 1 }}>
        <Box sx={{ minWidth: 0, flex: "1 1 200px" }}>
          {vm.workspaceLoading ? (
            <Box sx={{ display: "inline-flex", alignItems: "center", gap: 1 }}>
              <CircularProgress size={16} sx={{ color: tk.accent.fg }} />
              <Typography component="span" sx={{ fontSize: "0.8125rem", color: tk.text.secondary }}>
                {t("workspace.header.loadingWs")}
              </Typography>
            </Box>
          ) : hasWs ? (
            <>
              <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary, lineHeight: 1.25 }} noWrap>
                {vm.workspaceMeta.name || t("workspace.header.titleFallback")}
              </Typography>
              <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, mt: 0.25 }}>
                {vm.effectiveWorkIds.length === 1
                  ? t("workspace.header.paperCountOne", { count: String(vm.effectiveWorkIds.length) })
                  : t("workspace.header.paperCountMany", { count: String(vm.effectiveWorkIds.length) })}
              </Typography>
              {multiPapers && vm.selectedWorkId ? (
                <Typography sx={{ fontSize: "0.72rem", color: tk.text.secondary, mt: 0.35, lineHeight: 1.35 }} noWrap title={focusedTitle || ""}>
                  <Box component="span" sx={{ color: tk.text.accent }}>
                    {t("workspace.header.focusedPaper")}{" "}
                  </Box>
                  {focusedTitle || t("workspace.paper.noTitle")}
                </Typography>
              ) : null}
            </>
          ) : (
            <>
              <Typography sx={{ fontSize: "0.68rem", fontWeight: 700, color: tk.text.muted, letterSpacing: "0.02em" }}>
                {t("workspace.header.eyebrow")}
              </Typography>
              <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary, mt: 0.25 }}>
                {t("workspace.header.titleFallback")}
              </Typography>
              <Box sx={{ mt: 0.75 }}>
                <WorkIdGlossaryHint variant="workspace" />
              </Box>
              <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, mt: 0.75, lineHeight: 1.45 }}>
                {t("workspace.hero.switchWorkspaceHint")}
              </Typography>
            </>
          )}
        </Box>

        {hasWs && gs ? <WorkspaceStripGraphStats tk={tk} t={t} graphStats={gs} /> : null}

        <WorkspaceIngestProgressStrip
          tk={tk}
          t={t}
          hasWs={hasWs}
          ingestBusy={ingestBusy}
          progressValue={progressValue}
          ingestIndeterminate={ingestIndeterminate}
          ingestStrip={ingestStrip}
          ingestStageSecondary={ingestStageSecondary}
          ingestPhaseIdx={ingestPhaseIdx}
        />

        {hasWs ? (
          <Stack
            direction="row"
            alignItems="center"
            gap={0.75}
            flexWrap="wrap"
            sx={{ ml: { xs: 0, md: "auto" }, flexShrink: 0 }}
          >
            <WorkspaceIngestMenu
              workspaceId={vm.workspaceMeta.id}
              uploadBusy={vm.uploadBusy}
              ingestJobId={vm.ingestJobId}
              ingestJob={vm.ingestJob}
              ingestErr={vm.ingestErr}
              onUploadDocument={vm.handleUploadDocument}
              onUploadBatch={vm.handleUploadBatch}
              addWorkInput={vm.addWorkInput}
              onAddWorkInputChange={vm.setAddWorkInput}
              addBusy={vm.addBusy}
              onAddWork={vm.handleAddWork}
              menuButtonAria={t("workspace.strip.addMenuAria")}
              menuButtonTooltip={t("workspace.strip.addMenuTooltip")}
            />
            {actionGroups.map((el, i) => (
              <React.Fragment key={i}>{el}</React.Fragment>
            ))}
            <CopyIdButton
              id={vm.workspaceMeta.id}
              tooltipCopy={t("workspace.tooltip.copyWorkspaceId")}
              tooltipCopied={t("workspace.tooltip.copied")}
            />
          </Stack>
        ) : null}
      </Stack>
    </Box>
  );
}
