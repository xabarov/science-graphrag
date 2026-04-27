import { useEffect, useMemo, useState } from "react";

import {
  getBenchmarkCaseArtifacts,
  getBenchmarkCaseDetail,
  getBenchmarkRunCaseDetail,
} from "../../../services/benchmarkApi.js";

import { buildEvidenceLinksFromArtifacts, buildFixtureCatalogHighlights } from "./benchmarkCaseInspectorModel.js";

/**
 * Loads run-scoped case detail or fixture catalog detail for the case inspector.
 * @param {{ selectedRunId: string | null, selectedCaseId: string | null, caseFamily: string }} args
 */
export function useBenchmarkCaseInspectorData({ selectedRunId, selectedCaseId, caseFamily }) {
  const [runCaseDetail, setRunCaseDetail] = useState(/** @type {Record<string, unknown> | null} */ (null));
  const [fixtureDetail, setFixtureDetail] = useState(/** @type {Record<string, unknown> | null} */ (null));
  const [fixtureArtifacts, setFixtureArtifacts] = useState(/** @type {Record<string, unknown> | null} */ (null));
  const [fixtureGoldSource, setFixtureGoldSource] = useState("curated_gold");
  const [error, setError] = useState(/** @type {string | null} */ (null));
  const [loading, setLoading] = useState(false);

  const mode = selectedRunId && selectedCaseId ? "run" : selectedCaseId ? "fixture" : "idle";

  useEffect(() => {
    setFixtureGoldSource("curated_gold");
  }, [selectedCaseId, caseFamily]);

  useEffect(() => {
    if (selectedRunId) {
      setFixtureDetail(null);
      setFixtureArtifacts(null);
    }
  }, [selectedRunId]);

  useEffect(() => {
    if (!selectedCaseId || !selectedRunId) {
      setRunCaseDetail(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const resp = await getBenchmarkRunCaseDetail(selectedRunId, selectedCaseId);
        const data = resp?.data || resp;
        if (!cancelled) setRunCaseDetail(data && typeof data === "object" ? data : null);
      } catch (e) {
        if (!cancelled) {
          setRunCaseDetail(null);
          setError(e?.message || "failed_to_load_case_detail");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedRunId, selectedCaseId]);

  useEffect(() => {
    if (!selectedCaseId || selectedRunId) {
      setFixtureDetail(null);
      setFixtureArtifacts(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    const fam = (caseFamily || "layer1").trim().toLowerCase();
    (async () => {
      try {
        const [artResp, detResp] = await Promise.all([
          getBenchmarkCaseArtifacts(selectedCaseId, { family: fam }),
          getBenchmarkCaseDetail(selectedCaseId, {
            family: fam,
            gold_source: fam === "layer1" || fam === "graph" ? fixtureGoldSource : undefined,
          }),
        ]);
        if (cancelled) return;
        setFixtureArtifacts(artResp && typeof artResp === "object" ? artResp : null);
        setFixtureDetail(detResp && typeof detResp === "object" ? detResp : null);
      } catch (e) {
        if (!cancelled) {
          setFixtureDetail(null);
          setFixtureArtifacts(null);
          setError(e?.message || "failed_to_load_fixture_case");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedCaseId, selectedRunId, caseFamily, fixtureGoldSource]);

  const normalizedCaseDetail = useMemo(() => {
    if (mode === "run") return runCaseDetail;
    if (mode !== "fixture" || !fixtureDetail) return null;
    const d = fixtureDetail;
    const evidence = buildEvidenceLinksFromArtifacts(fixtureArtifacts);
    const hl = buildFixtureCatalogHighlights(caseFamily || "layer1");
    return {
      case_id: selectedCaseId,
      family: (caseFamily || "layer1").trim().toLowerCase(),
      status: null,
      summary: {},
      article: {
        raw_markdown: d.article_md || "",
        sections: d.article_sections || [],
      },
      gold: {
        source: fixtureGoldSource,
        payload: d.gold || {},
      },
      predicted: { payload: null },
      comparison: {},
      metrics: {},
      diagnostics: {},
      run_config: {},
      highlights: hl,
      evidence_links: evidence,
    };
  }, [mode, runCaseDetail, fixtureDetail, fixtureArtifacts, caseFamily, selectedCaseId, fixtureGoldSource]);

  return {
    mode,
    loading,
    error,
    caseDetail: normalizedCaseDetail,
    fixtureDetail,
    fixtureArtifacts,
    fixtureGoldSource,
    setFixtureGoldSource,
  };
}
