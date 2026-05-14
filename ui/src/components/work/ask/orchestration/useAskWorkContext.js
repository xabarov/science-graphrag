import { useCallback, useEffect, useRef, useState } from "react";

import { getWorkDetail, getWorks } from "../../../../services/researchApi.js";
import { persistWorkId } from "../../../../pages/WorkspacePage/utils/workContext.js";
import { getWorkspace } from "../../../../utils/workspaceStore.js";
import { normalizeWorkListItem } from "../answer/workListLabel.js";

/**
 * Workspace work search, article picker, and work chip hydration for Ask.
 *
 * @param {{
 *   workspaceId: string,
 *   locked: boolean,
 *   workId: string,
 *   setWorkId: (id: string) => void,
 * }} args
 * @returns {{
 *   workDetailsForChip: unknown,
 *   workspaceSearchOptions: unknown[],
 *   searchWorks: (q: string) => Promise<unknown[]>,
 *   onArticlePicked: (item: unknown) => void,
 *   handleWorkIdChange: (next: string) => void,
 * }}
 */
export function useAskWorkContext({ workspaceId, locked, workId, setWorkId }) {
  const [workDetailsForChip, setWorkDetailsForChip] = useState(null);
  const [workspaceSearchOptions, setWorkspaceSearchOptions] = useState([]);
  const skipHydrateWorkRef = useRef(false);

  const searchWorks = useCallback(
    async (q) => {
      const needle = String(q || "").trim().toLowerCase();
      if (workspaceId) {
        if (!needle) return workspaceSearchOptions;
        return workspaceSearchOptions.filter((item) => {
          const row = normalizeWorkListItem(item);
          return [
            row.title,
            row.doi,
            row.arxiv_id,
            row.venue,
            row.work_id,
            row.year != null ? String(row.year) : "",
          ]
            .filter(Boolean)
            .some((part) => String(part).toLowerCase().includes(needle));
        });
      }
      const res = await getWorks({ q: (q || "").trim(), limit: 40, offset: 0 });
      return res.data?.items || [];
    },
    [workspaceId, workspaceSearchOptions],
  );

  const onArticlePicked = useCallback((item) => {
    const row = normalizeWorkListItem(item);
    if (!row.work_id) return;
    const rich = Boolean(row.title || row.doi || row.arxiv_id || row.venue);
    if (rich) {
      skipHydrateWorkRef.current = true;
      setWorkDetailsForChip(row);
    }
    setWorkId(row.work_id);
  }, [setWorkId]);

  const handleWorkIdChange = useCallback(
    (next) => {
      setWorkId(next);
      if (!String(next || "").trim()) setWorkDetailsForChip(null);
    },
    [setWorkId],
  );

  useEffect(() => {
    if (!workspaceId || locked) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- reset options when leaving workspace scope
      setWorkspaceSearchOptions([]);
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const ws = await getWorkspace(workspaceId);
        if (cancelled) return;
        const ids = Array.isArray(ws?.work_ids) ? ws.work_ids.map((x) => String(x || "").trim()).filter(Boolean) : [];
        if (!ids.length) {
          setWorkspaceSearchOptions([]);
          return;
        }
        const details = await Promise.all(
          ids.map(async (wid) => {
            try {
              const res = await getWorkDetail(wid);
              return normalizeWorkListItem(res.data || {}, wid);
            } catch {
              return normalizeWorkListItem({ work_id: wid }, wid);
            }
          }),
        );
        if (!cancelled) setWorkspaceSearchOptions(details);
      } catch {
        if (!cancelled) setWorkspaceSearchOptions([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workspaceId, locked]);

  useEffect(() => {
    const w = String(workId || "").trim();
    if (!w) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- clear chip when work id empty
      setWorkDetailsForChip(null);
      return undefined;
    }
    if (skipHydrateWorkRef.current) {
      skipHydrateWorkRef.current = false;
      return undefined;
    }
    let cancelled = false;
    const tid = setTimeout(() => {
      getWorkDetail(w)
        .then((res) => {
          if (!cancelled) setWorkDetailsForChip(normalizeWorkListItem(res.data || {}, w));
        })
        .catch(() => {
          if (!cancelled) setWorkDetailsForChip(normalizeWorkListItem({ work_id: w }, w));
        });
    }, 220);
    return () => {
      cancelled = true;
      clearTimeout(tid);
    };
  }, [workId]);

  useEffect(() => {
    if (!locked && workId.trim()) persistWorkId(workId);
  }, [locked, workId]);

  return {
    workDetailsForChip,
    workspaceSearchOptions,
    searchWorks,
    onArticlePicked,
    handleWorkIdChange,
  };
}
