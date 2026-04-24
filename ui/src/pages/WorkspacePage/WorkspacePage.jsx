import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";

import { CursorPrimaryButton, CursorSmallButton } from "../../components/common/index.js";
import PageHeader from "../../components/layout/PageHeader.jsx";
import WorkIdGlossaryHint from "../../components/layout/WorkIdGlossaryHint.jsx";
import { mainShellContentSx } from "../../components/layout/mainShellContentSx.js";
import { formatResearchApiError, getWorkDetail } from "../../services/researchApi.js";
import {
  getActiveWorkspaceId,
  setActiveWorkspaceId,
  listWorkspaces,
  getWorkspace,
  addWorkToWorkspace,
  getIngestJob,
  startWorkspaceDocumentIngest,
} from "../../utils/workspaceStore.js";
import { persistWorkId, resolveSelectedWorkId } from "./utils/workContext.js";
import { rememberRecentWork } from "../HomePage/homeState.js";
import { useI18n } from "../../i18n/I18nContext.jsx";
import WorkspaceDedupSection from "./WorkspaceDedupSection.jsx";
import WorkspaceIngestPanel from "./WorkspaceIngestPanel.jsx";
import WorkspacePaperList from "./WorkspacePaperList.jsx";
import { workGraphUrl } from "./workspacePageUrls.js";

export default function WorkspacePage() {
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const workspaceIdFromUrl = (searchParams.get("workspace_id") || "").trim();
  const workIdFromUrl = (searchParams.get("work_id") || "").trim();

  const [workspaceMeta, setWorkspaceMeta] = useState({ id: "", name: "", work_ids: [] });
  const [workspaceLoading, setWorkspaceLoading] = useState(true);
  const [workspaceError, setWorkspaceError] = useState(null);
  const [addWorkInput, setAddWorkInput] = useState("");
  const [addBusy, setAddBusy] = useState(false);
  const [addErr, setAddErr] = useState(null);

  const [papers, setPapers] = useState(() => new Map());
  const [ingestJobId, setIngestJobId] = useState("");
  const [ingestJob, setIngestJob] = useState(null);
  const [ingestErr, setIngestErr] = useState(null);
  const [uploadBusy, setUploadBusy] = useState(false);

  const refreshWorkspaceMeta = useCallback(async () => {
    const id = workspaceMeta.id;
    if (!id) return;
    try {
      const ws = await getWorkspace(id);
      if (ws) setWorkspaceMeta(ws);
    } catch {
      /* ignore */
    }
  }, [workspaceMeta.id]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setWorkspaceLoading(true);
      setWorkspaceError(null);
      try {
        const list = await listWorkspaces();
        if (cancelled) return;
        let activeId = workspaceIdFromUrl || getActiveWorkspaceId();
        if (!activeId && list.length) activeId = list[0].id;
        if (!activeId) {
          setWorkspaceMeta({ id: "", name: "", work_ids: [] });
          return;
        }
        setActiveWorkspaceId(activeId);
        const ws = await getWorkspace(activeId);
        if (cancelled) return;
        if (!ws) {
          setWorkspaceError(t("workspace.err.notFound"));
          setWorkspaceMeta({ id: "", name: "", work_ids: [] });
          return;
        }
        setWorkspaceMeta(ws);
        const nextParams = new URLSearchParams();
        nextParams.set("workspace_id", ws.id);
        const ids = Array.isArray(ws.work_ids) ? ws.work_ids : [];
        if (ids.length === 1) {
          nextParams.set("work_id", ids[0]);
        } else if (workIdFromUrl && ids.includes(workIdFromUrl)) {
          nextParams.set("work_id", workIdFromUrl);
        }
        setSearchParams(nextParams, { replace: true });
      } catch (e) {
        if (!cancelled) setWorkspaceError(formatResearchApiError(e));
      } finally {
        if (!cancelled) setWorkspaceLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workspaceIdFromUrl, workIdFromUrl, setSearchParams, t]);

  const effectiveWorkIds = useMemo(() => {
    const fromWs = Array.isArray(workspaceMeta.work_ids) ? workspaceMeta.work_ids : [];
    if (fromWs.length) return fromWs;
    return [];
  }, [workspaceMeta.work_ids]);

  const selectedWorkId = useMemo(
    () => resolveSelectedWorkId({ workIds: effectiveWorkIds, workIdFromUrl }),
    [effectiveWorkIds, workIdFromUrl],
  );

  const setWorkFocusInUrl = useCallback(
    (wid) => {
      const w = String(wid || "").trim();
      if (!workspaceMeta.id || !w) return;
      const p = new URLSearchParams();
      p.set("workspace_id", workspaceMeta.id);
      p.set("work_id", w);
      setSearchParams(p, { replace: true });
    },
    [workspaceMeta.id, setSearchParams],
  );

  const workIdsKey = effectiveWorkIds.join("|");

  useEffect(() => {
    if (!effectiveWorkIds.length) return undefined;
    let cancelled = false;
    (async () => {
      for (const wid of effectiveWorkIds) {
        setPapers((prev) => {
          const m = new Map(prev);
          const cur = m.get(wid) || {};
          m.set(wid, { ...cur, workId: wid, loading: true, error: null });
          return m;
        });
        try {
          const res = await getWorkDetail(wid);
          if (cancelled) return;
          const d = res.data;
          setPapers((prev) => {
            const m = new Map(prev);
            m.set(wid, {
              workId: wid,
              title: typeof d?.title === "string" ? d.title : "",
              year: d?.year ?? null,
              doi: d?.doi ?? null,
              arxivId: d?.arxiv_id ?? null,
              loading: false,
              error: null,
            });
            return m;
          });
          rememberRecentWork({
            workId: wid,
            title: typeof d?.title === "string" ? d.title : "",
            year: d?.year ?? null,
            tab: "overview",
            workspaceId: workspaceMeta.id || "",
          });
        } catch (err) {
          if (cancelled) return;
          setPapers((prev) => {
            const m = new Map(prev);
            m.set(wid, {
              workId: wid,
              title: "",
              loading: false,
              error: formatResearchApiError(err),
            });
            return m;
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workIdsKey, effectiveWorkIds, workspaceMeta.id]);

  useEffect(() => {
    if (selectedWorkId) persistWorkId(selectedWorkId);
  }, [selectedWorkId]);

  useEffect(() => {
    if (!ingestJobId) return undefined;
    let cancelled = false;
    const tick = async () => {
      try {
        const j = await getIngestJob(ingestJobId);
        if (cancelled) return;
        setIngestJob(j);
        if (j?.status === "completed" || j?.status === "failed") {
          await refreshWorkspaceMeta();
          setIngestJobId("");
        }
      } catch {
        /* ignore transient poll errors */
      }
    };
    tick();
    const id = setInterval(tick, 2000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [ingestJobId, refreshWorkspaceMeta]);

  const emptyState = useMemo(
    () => (
      <Box sx={{ maxWidth: 560, mt: 2 }}>
        <Alert severity="info" sx={{ fontSize: "0.8125rem", mb: 2, backgroundColor: "rgba(99,102,241,0.08)", color: "rgba(255,255,255,0.85)" }}>
          {t("workspace.empty.alert")}
        </Alert>
        <CursorPrimaryButton component={Link} to="/workspaces" sx={{ textDecoration: "none" }}>
          {t("workspace.empty.workspaces")}
        </CursorPrimaryButton>
        <CursorSmallButton component={Link} to="/home" sx={{ textDecoration: "none", ml: 1 }}>
          {t("workspace.empty.about")}
        </CursorSmallButton>
      </Box>
    ),
    [t],
  );

  async function handleAddWork(e) {
    e?.preventDefault?.();
    const raw = addWorkInput.trim();
    if (!raw || !workspaceMeta.id) return;
    setAddBusy(true);
    setAddErr(null);
    try {
      await addWorkToWorkspace(workspaceMeta.id, raw);
      setAddWorkInput("");
      const ws = await getWorkspace(workspaceMeta.id);
      if (ws) setWorkspaceMeta(ws);
    } catch (err) {
      setAddErr(formatResearchApiError(err));
    } finally {
      setAddBusy(false);
    }
  }

  async function handleUploadDocument(ev) {
    const file = ev.target.files?.[0];
    ev.target.value = "";
    if (!file || !workspaceMeta.id) return;
    setUploadBusy(true);
    setIngestErr(null);
    try {
      const job = await startWorkspaceDocumentIngest(workspaceMeta.id, file);
      const jid = String(job?.job_id || "").trim();
      if (jid) {
        setIngestJob(job);
        setIngestJobId(jid);
      }
    } catch (err) {
      setIngestErr(formatResearchApiError(err));
    } finally {
      setUploadBusy(false);
    }
  }

  const onCardActivate =
    workspaceMeta.id && effectiveWorkIds.length > 1 ? (wid) => setWorkFocusInUrl(wid) : undefined;

  return (
    <Box sx={{ p: { xs: 1.5, sm: 2 }, ...mainShellContentSx }}>
      <PageHeader
        eyebrow={t("workspace.header.eyebrow")}
        title={workspaceMeta.name || t("workspace.header.titleFallback")}
        description={
          workspaceLoading ? (
            <Box sx={{ display: "inline-flex", alignItems: "center", gap: 1 }}>
              <CircularProgress size={18} sx={{ color: "rgba(129,140,248,0.9)" }} />
              <span>{t("workspace.header.loadingWs")}</span>
            </Box>
          ) : workspaceMeta.id ? (
            <>
              <span style={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem" }}>
                {effectiveWorkIds.length === 1
                  ? t("workspace.header.paperCountOne", { count: String(effectiveWorkIds.length) })
                  : t("workspace.header.paperCountMany", { count: String(effectiveWorkIds.length) })}
                {effectiveWorkIds.length > 1 && selectedWorkId ? (
                  <>
                    <br />
                    <span style={{ color: "rgba(129,140,248,0.95)" }}>{t("workspace.header.focusedPaper")} </span>
                    <span>{papers.get(selectedWorkId)?.title || selectedWorkId}</span>
                  </>
                ) : null}
              </span>
              <br />
              <span style={{ color: "rgba(255,255,255,0.38)", fontFamily: "monospace", fontSize: "0.72rem" }}>
                {workspaceMeta.id}
              </span>
            </>
          ) : (
            <WorkIdGlossaryHint variant="workspace" />
          )
        }
        actions={
          workspaceMeta.id ? (
            <CursorSmallButton component={Link} to={workGraphUrl("", workspaceMeta.id)} sx={{ textDecoration: "none" }}>
              {t("workspace.header.workspaceGraph")}
            </CursorSmallButton>
          ) : null
        }
      />

      {workspaceError ? (
        <Alert severity="error" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {workspaceError}
        </Alert>
      ) : null}

      {!workspaceLoading && !workspaceMeta.id ? (
        emptyState
      ) : (
        <>
          <WorkspaceIngestPanel
            workspaceId={workspaceMeta.id}
            uploadBusy={uploadBusy}
            ingestJobId={ingestJobId}
            ingestJob={ingestJob}
            ingestErr={ingestErr}
            onUploadDocument={handleUploadDocument}
            addWorkInput={addWorkInput}
            onAddWorkInputChange={setAddWorkInput}
            addBusy={addBusy}
            onAddWork={handleAddWork}
          />
          {addErr ? (
            <Alert severity="warning" sx={{ mb: 2, fontSize: "0.8125rem" }}>
              {addErr}
            </Alert>
          ) : null}

          <WorkspacePaperList
            workspaceId={workspaceMeta.id}
            effectiveWorkIds={effectiveWorkIds}
            papers={papers}
            selectedWorkId={selectedWorkId}
            onCardActivate={onCardActivate}
          />

          <WorkspaceDedupSection workspaceId={workspaceMeta.id} onMerged={() => refreshWorkspaceMeta()} />
        </>
      )}
    </Box>
  );
}