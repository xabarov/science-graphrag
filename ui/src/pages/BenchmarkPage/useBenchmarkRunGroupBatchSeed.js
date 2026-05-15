import { useEffect, useRef } from "react";

import {
  getExperimentsForPack,
  getLauncherPresetForExperiment,
  getUiRunnableExperiments,
  RUN_MODE_GROUPED,
} from "./experimentCatalog.js";

/**
 * Seeds default batch experiment + model profile selection when entering grouped mode.
 *
 * @param {object} opts
 * @param {"single"|"grouped"} opts.executionMode
 * @param {{ packId: string | null }} opts.runLabQuery
 * @param {string} opts.activeFamilyModelProfile
 * @param {import("react").Dispatch<import("react").SetStateAction<string[]>>} opts.setBatchExperimentIds
 * @param {import("react").Dispatch<import("react").SetStateAction<string[]>>} opts.setBatchModelProfileIds
 */
export function useBenchmarkRunGroupBatchSeed({
  executionMode,
  runLabQuery,
  activeFamilyModelProfile,
  setBatchExperimentIds,
  setBatchModelProfileIds,
}) {
  const seededPackRef = useRef(/** @type {string | null} */ (null));
  const defaultBatchExperimentsSeededRef = useRef(false);
  const batchModelsSeededRef = useRef(false);

  useEffect(() => {
    if (executionMode !== RUN_MODE_GROUPED || !runLabQuery.packId) return;
    if (seededPackRef.current === runLabQuery.packId) return;
    seededPackRef.current = runLabQuery.packId;
    defaultBatchExperimentsSeededRef.current = true;
    const fromPack = getExperimentsForPack(runLabQuery.packId)
      .map((e) => e.id)
      .filter((id) => Boolean(getLauncherPresetForExperiment(id)));
    setBatchExperimentIds(fromPack);
  }, [executionMode, runLabQuery.packId, setBatchExperimentIds]);

  useEffect(() => {
    if (executionMode !== RUN_MODE_GROUPED) {
      defaultBatchExperimentsSeededRef.current = false;
      return;
    }
    if (runLabQuery.packId) return;
    if (defaultBatchExperimentsSeededRef.current) return;
    defaultBatchExperimentsSeededRef.current = true;
    setBatchExperimentIds(getUiRunnableExperiments().map((e) => e.id));
  }, [executionMode, runLabQuery.packId, setBatchExperimentIds]);

  useEffect(() => {
    if (executionMode !== RUN_MODE_GROUPED) {
      batchModelsSeededRef.current = false;
      return;
    }
    if (batchModelsSeededRef.current) return;
    batchModelsSeededRef.current = true;
    const mp = activeFamilyModelProfile || "env_default";
    setBatchModelProfileIds([mp]);
  }, [executionMode, activeFamilyModelProfile, setBatchModelProfileIds]);
}
