import { useEffect, useRef, useState } from "react";

import { postGraphSnapshotPreview } from "../../../services/benchmarkApi.js";
import { formatResearchApiError } from "../../../services/researchApi.js";

/**
 * Local state for graph_expectations tab: loaded CLI JSON file + optional server preview.
 * @param {object} args
 * @param {boolean} args.open
 * @param {string | null} args.caseId
 * @param {string} args.family Benchmark family (for resetting when case/family changes).
 * @param {"layer1" | "graph" | null} args.graphSnapshotApiFamily
 */
export function useGraphSnapshotLocalState({ open, caseId, family, graphSnapshotApiFamily }) {
  const [snapshotJson, setSnapshotJson] = useState(null);
  const [snapshotLoadError, setSnapshotLoadError] = useState(null);
  const [serverPreview, setServerPreview] = useState(null);
  const [serverPreviewLoading, setServerPreviewLoading] = useState(false);
  const [serverPreviewError, setServerPreviewError] = useState(null);
  const snapshotFileRef = useRef(null);

  useEffect(() => {
    if (!open) {
      setSnapshotJson(null);
      setSnapshotLoadError(null);
    }
  }, [open]);

  useEffect(() => {
    setSnapshotJson(null);
    setSnapshotLoadError(null);
    setServerPreview(null);
    setServerPreviewError(null);
  }, [caseId, family]);

  useEffect(() => {
    setServerPreview(null);
    setServerPreviewError(null);
  }, [snapshotJson]);

  const loadSnapshotFromFile = (file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result || ""));
        setSnapshotJson(parsed);
        setSnapshotLoadError(null);
      } catch (err) {
        setSnapshotJson(null);
        setSnapshotLoadError(err?.message || "invalid_json");
      }
    };
    reader.readAsText(file);
  };

  const clearSnapshot = () => {
    setSnapshotJson(null);
    setSnapshotLoadError(null);
  };

  const requestServerPreview = async () => {
    if (!snapshotJson || !caseId || !graphSnapshotApiFamily) return;
    setServerPreviewLoading(true);
    setServerPreviewError(null);
    try {
      const resp = await postGraphSnapshotPreview(caseId, snapshotJson, {
        family: graphSnapshotApiFamily,
      });
      const payload = resp?.data || resp;
      setServerPreview(payload);
    } catch (err) {
      setServerPreviewError(formatResearchApiError(err) || "server_preview_failed");
    } finally {
      setServerPreviewLoading(false);
    }
  };

  return {
    snapshotJson,
    snapshotLoadError,
    serverPreview,
    serverPreviewLoading,
    serverPreviewError,
    snapshotFileRef,
    loadSnapshotFromFile,
    clearSnapshot,
    requestServerPreview,
  };
}
