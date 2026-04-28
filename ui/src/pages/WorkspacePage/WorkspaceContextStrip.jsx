import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import LightbulbOutlinedIcon from "@mui/icons-material/LightbulbOutlined";
import QuestionAnswerIcon from "@mui/icons-material/QuestionAnswer";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

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
import { ShimmerLabel } from "../../components/work/ShimmerLabel.jsx";
import { workChatUrl, workGraphUrl } from "./workspacePageUrls.js";
import WorkspaceIngestMenu from "./WorkspaceIngestMenu.jsx";

/**
 * Single compact command strip for workspace overview (Cursor-like).
 * Workspace selection lives in shell only — no duplicate WorkspaceSwitcher here.
 *
 * @param {{ t: (key: string, vars?: Record<string, string>) => string, vm: Record<string, unknown> }} props
 */
export default function WorkspaceContextStrip({ t, vm }) {
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
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "rgba(255,255,255,0.02)",
      }}
    >
      <Stack direction="row" flexWrap="wrap" alignItems="center" gap={1} useFlexGap sx={{ rowGap: 1 }}>
        <Box sx={{ minWidth: 0, flex: "1 1 200px" }}>
          {vm.workspaceLoading ? (
            <Box sx={{ display: "inline-flex", alignItems: "center", gap: 1 }}>
              <CircularProgress size={16} sx={{ color: "rgba(129,140,248,0.9)" }} />
              <Typography component="span" sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.65)" }}>
                {t("workspace.header.loadingWs")}
              </Typography>
            </Box>
          ) : hasWs ? (
            <>
              <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: "rgba(255,255,255,0.92)", lineHeight: 1.25 }} noWrap>
                {vm.workspaceMeta.name || t("workspace.header.titleFallback")}
              </Typography>
              <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.48)", mt: 0.25 }}>
                {vm.effectiveWorkIds.length === 1
                  ? t("workspace.header.paperCountOne", { count: String(vm.effectiveWorkIds.length) })
                  : t("workspace.header.paperCountMany", { count: String(vm.effectiveWorkIds.length) })}
              </Typography>
              {multiPapers && vm.selectedWorkId ? (
                <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.55)", mt: 0.35, lineHeight: 1.35 }} noWrap title={focusedTitle || ""}>
                  <Box component="span" sx={{ color: "rgba(129,140,248,0.9)" }}>
                    {t("workspace.header.focusedPaper")}{" "}
                  </Box>
                  {focusedTitle || t("workspace.paper.noTitle")}
                </Typography>
              ) : null}
            </>
          ) : (
            <>
              <Typography sx={{ fontSize: "0.68rem", fontWeight: 700, color: "rgba(255,255,255,0.42)", letterSpacing: "0.02em" }}>
                {t("workspace.header.eyebrow")}
              </Typography>
              <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: "rgba(255,255,255,0.88)", mt: 0.25 }}>
                {t("workspace.header.titleFallback")}
              </Typography>
              <Box sx={{ mt: 0.75 }}>
                <WorkIdGlossaryHint variant="workspace" />
              </Box>
              <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.45)", mt: 0.75, lineHeight: 1.45 }}>
                {t("workspace.hero.switchWorkspaceHint")}
              </Typography>
            </>
          )}
        </Box>

        {hasWs && gs ? (
          <>
            <Divider orientation="vertical" flexItem sx={{ borderColor: "rgba(255,255,255,0.08)", alignSelf: "stretch", minHeight: 28, display: { xs: "none", sm: "block" } }} />
            <Stack direction="row" flexWrap="wrap" gap={0.5} useFlexGap sx={{ alignItems: "center" }}>
              <Tooltip title={t("workspace.strip.statsWorksTip")}>
                <Chip
                  size="small"
                  label={t("workspace.strip.statsWorks", { count: String(gs.works_count ?? "—") })}
                  sx={{
                    height: 24,
                    fontSize: "0.6875rem",
                    borderRadius: "6px",
                    border: "1px solid rgba(255,255,255,0.1)",
                    backgroundColor: "rgba(255,255,255,0.04)",
                    "& .MuiChip-label": { px: 0.75 },
                  }}
                />
              </Tooltip>
              <Tooltip title={t("workspace.strip.statsAuthorsTip")}>
                <Chip
                  size="small"
                  label={t("workspace.strip.statsAuthors", { count: String(gs.authors_count ?? "—") })}
                  sx={{
                    height: 24,
                    fontSize: "0.6875rem",
                    borderRadius: "6px",
                    border: "1px solid rgba(255,255,255,0.1)",
                    backgroundColor: "rgba(255,255,255,0.04)",
                    "& .MuiChip-label": { px: 0.75 },
                  }}
                />
              </Tooltip>
              <Tooltip title={t("workspace.strip.statsInternalTip")}>
                <Chip
                  size="small"
                  label={t("workspace.strip.statsInternal", { count: String(gs.internal_citations ?? "—") })}
                  sx={{
                    height: 24,
                    fontSize: "0.6875rem",
                    borderRadius: "6px",
                    border: "1px solid rgba(255,255,255,0.1)",
                    backgroundColor: "rgba(255,255,255,0.04)",
                    "& .MuiChip-label": { px: 0.75 },
                  }}
                />
              </Tooltip>
              <Tooltip title={t("workspace.strip.statsExternalTip")}>
                <Chip
                  size="small"
                  label={t("workspace.strip.statsExternal", { count: String(gs.external_citations ?? "—") })}
                  sx={{
                    height: 24,
                    fontSize: "0.6875rem",
                    borderRadius: "6px",
                    border: "1px solid rgba(255,255,255,0.1)",
                    backgroundColor: "rgba(255,255,255,0.04)",
                    "& .MuiChip-label": { px: 0.75 },
                  }}
                />
              </Tooltip>
            </Stack>
          </>
        ) : null}

        {hasWs && ingestBusy ? (
          <Box sx={{ width: { xs: "100%", md: 260 }, flexShrink: 0, minWidth: 0 }}>
            <Tooltip
              title={
                <Stack spacing={0.75} sx={{ maxWidth: 280 }}>
                  <Typography sx={{ fontSize: "0.75rem", fontWeight: 600, color: "rgba(255,255,255,0.92)" }}>
                    {t("workspace.strip.ingestProgressTip")}
                  </Typography>
                  <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.65)", lineHeight: 1.45 }}>
                    {t("workspace.strip.ingestProgressTwoScalesHint")}
                  </Typography>
                </Stack>
              }
            >
              <Stack spacing={0.35}>
                <Stack direction="row" alignItems="center" justifyContent="space-between" gap={0.5}>
                  <Box sx={{ minWidth: 0, flex: 1 }}>
                    {ingestStrip?.failed ? (
                      <Typography sx={{ fontSize: "0.72rem", color: "rgba(239,68,68,0.88)", fontWeight: 500 }} noWrap>
                        {t("workspace.strip.ingestFailed")}
                      </Typography>
                    ) : ingestStrip?.starting ? (
                      <ShimmerLabel component="span" sx={{ fontSize: "0.72rem", fontWeight: 500 }}>
                        {t("workspace.strip.ingestStarting")}
                      </ShimmerLabel>
                    ) : (
                      <ShimmerLabel component="span" sx={{ fontSize: "0.72rem", fontWeight: 500 }}>
                        {t(`workspace.strip.ingestPhase.${ingestStrip?.phaseKey || "preparing_document"}`)}
                      </ShimmerLabel>
                    )}
                  </Box>
                  {!ingestIndeterminate && progressValue != null ? (
                    <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.42)", flexShrink: 0 }}>
                      {`${Math.round(progressValue)}%`}
                    </Typography>
                  ) : null}
                </Stack>
                {(() => {
                  if (ingestStrip.starting || ingestStrip.failed) return null;
                  const j = ingestStrip.job;
                  const dm = j?.detail_message && String(j.detail_message).trim();
                  const sc = typeof j?.subprogress_current === "number" ? j.subprogress_current : null;
                  const st = typeof j?.subprogress_total === "number" ? j.subprogress_total : null;
                  const subStr =
                    sc != null && st != null && st > 0 ? `${Math.round(sc)}/${Math.round(st)}` : null;
                  const core = dm || ingestStageSecondary || (j?.message ? String(j.message).slice(0, 72) : "");
                  const line = [subStr, core].filter(Boolean).join(" · ");
                  if (!line) return null;
                  return (
                    <Typography sx={{ fontSize: "0.65rem", color: "rgba(255,255,255,0.38)" }} noWrap title={ingestStrip.stageId}>
                      {line.length > 96 ? `${line.slice(0, 96)}…` : line}
                    </Typography>
                  );
                })()}
                <LinearProgress
                  variant={
                    ingestIndeterminate
                      ? "indeterminate"
                      : progressValue != null
                        ? "determinate"
                        : "indeterminate"
                  }
                  value={!ingestIndeterminate && progressValue != null ? progressValue : undefined}
                  sx={{
                    height: 4,
                    borderRadius: 2,
                    backgroundColor: "rgba(255,255,255,0.06)",
                    "& .MuiLinearProgress-bar": {
                      backgroundColor: ingestStrip?.failed ? "rgba(239,68,68,0.55)" : "rgba(99,102,241,0.75)",
                    },
                  }}
                />
                {!ingestStrip?.failed && !ingestStrip?.starting ? (
                  <Stack direction="row" spacing={0.35} sx={{ mt: 0.4 }} aria-hidden>
                    {INGEST_PHASE_KEYS.map((pk, i) => {
                      const done = i < ingestPhaseIdx;
                      const active = i === ingestPhaseIdx;
                      return (
                        <Box
                          key={pk}
                          sx={{
                            flex: 1,
                            height: 3,
                            borderRadius: 1,
                            backgroundColor:
                              done || active ? "rgba(99,102,241,0.5)" : "rgba(255,255,255,0.06)",
                            opacity: active ? 1 : done ? 0.85 : 1,
                          }}
                        />
                      );
                    })}
                  </Stack>
                ) : null}
              </Stack>
            </Tooltip>
          </Box>
        ) : null}

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
