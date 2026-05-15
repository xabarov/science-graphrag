import { useEffect, useMemo } from "react";

import { getBenchmarkRun } from "../../services/benchmarkApi.js";
import {
  aggregateGroupStatus,
  BENCHMARK_TERMINAL_RUN_STATUSES,
  pushRecentCompareSetup,
  saveLastRunGroup,
} from "./benchmarkRunGroup.js";

/**
 * Poll non-terminal group child runs and finalize group metadata when all complete.
 *
 * @param {{
 *   groupChildrenRef: import("react").MutableRefObject<import("./benchmarkRunGroup.js").GroupChildRun[]>,
 *   groupChildren: import("./benchmarkRunGroup.js").GroupChildRun[],
 *   setGroupChildren: import("react").Dispatch<import("react").SetStateAction<import("./benchmarkRunGroup.js").GroupChildRun[]>>,
 *   groupMeta: { groupId: string, startedAt: number } | null,
 *   setRecentSetupsVersion: import("react").Dispatch<import("react").SetStateAction<number>>,
 *   finalizedGroupRef: import("react").MutableRefObject<string | null>,
 * }} opts
 */
export function useBenchmarkRunGroupPolling({
  groupChildrenRef,
  groupChildren,
  setGroupChildren,
  groupMeta,
  setRecentSetupsVersion,
  finalizedGroupRef,
}) {
  const needsGroupPoll = useMemo(
    () => groupChildren.some((c) => c.runId && !BENCHMARK_TERMINAL_RUN_STATUSES.includes(c.status)),
    [groupChildren],
  );

  useEffect(() => {
    if (!needsGroupPoll) return;
    let cancelled = false;
    async function tick() {
      const current = groupChildrenRef.current;
      const updates = await Promise.all(
        current.map(async (c) => {
          if (!c.runId || BENCHMARK_TERMINAL_RUN_STATUSES.includes(c.status)) return c;
          try {
            const resp = await getBenchmarkRun(c.runId);
            const payload = resp?.data || resp;
            return { ...c, status: payload?.status || c.status, run: payload };
          } catch {
            return c;
          }
        }),
      );
      if (!cancelled) setGroupChildren(updates);
    }
    void tick();
    const intervalId = window.setInterval(() => void tick(), 2000);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [needsGroupPoll, groupChildrenRef, setGroupChildren]);

  useEffect(() => {
    if (needsGroupPoll) return;
    if (!groupMeta?.groupId) return;
    if (!groupChildren.length) return;
    if (finalizedGroupRef.current === groupMeta.groupId) return;
    if (groupChildren.some((c) => c.status === "queued")) return;
    const allResolved = groupChildren.every(
      (c) => !c.runId || BENCHMARK_TERMINAL_RUN_STATUSES.includes(c.status),
    );
    if (!allResolved) return;
    finalizedGroupRef.current = groupMeta.groupId;
    const runIds = groupChildren.map((c) => c.runId).filter(Boolean);
    pushRecentCompareSetup({
      groupId: groupMeta.groupId,
      experimentIds: [...new Set(groupChildren.map((c) => c.experimentId))],
      modelProfileIds: [...new Set(groupChildren.map((c) => c.modelProfileId))],
      runIds,
    });
    saveLastRunGroup({
      groupId: groupMeta.groupId,
      startedAt: groupMeta.startedAt,
      completedAt: Date.now(),
      aggregateStatus: aggregateGroupStatus(groupChildren, BENCHMARK_TERMINAL_RUN_STATUSES),
      children: groupChildren,
    });
    if (runIds[0]) {
      window.localStorage.setItem("benchmark:lastRunId", runIds[0]);
    }
    setRecentSetupsVersion((v) => v + 1);
  }, [needsGroupPoll, groupMeta, groupChildren, finalizedGroupRef, setRecentSetupsVersion]);
}
