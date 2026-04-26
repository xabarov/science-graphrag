import React, { useMemo } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { useI18n } from "../../../i18n/useI18n.js";
import {
  compareGraphExpectationsToSnapshot,
  extractGraphSnapshotMetrics,
  graphExpectationRangeRows,
} from "../graphSnapshotCompare.js";
import CaseGraphExpectationsCompareAndServer from "./CaseGraphExpectationsCompareAndServer.jsx";
import CaseGraphExpectationsGoldColumn from "./CaseGraphExpectationsGoldColumn.jsx";
import CaseGraphExpectationsSnapshotColumn from "./CaseGraphExpectationsSnapshotColumn.jsx";
import CaseGraphExpectationsToolbar from "./CaseGraphExpectationsToolbar.jsx";
import { useGraphSnapshotLocalState } from "./useGraphSnapshotLocalState.js";

export default function CaseGraphExpectationsPanel({
  open,
  caseId,
  family,
  graphSnapshotApiFamily,
  detail,
}) {
  const { t } = useI18n();
  const {
    snapshotJson,
    snapshotLoadError,
    serverPreview,
    serverPreviewLoading,
    serverPreviewError,
    snapshotFileRef,
    loadSnapshotFromFile,
    clearSnapshot,
    requestServerPreview,
  } = useGraphSnapshotLocalState({ open, caseId, family, graphSnapshotApiFamily });

  const graphExpectations = detail?.gold?.graph_expectations;
  const graphExpectationsJson = useMemo(() => {
    if (!graphExpectations) return "";
    return JSON.stringify(graphExpectations, null, 2);
  }, [graphExpectations]);

  const snapshotMetrics = useMemo(() => extractGraphSnapshotMetrics(snapshotJson), [snapshotJson]);
  const graphCompare = useMemo(
    () => compareGraphExpectationsToSnapshot(graphExpectations, snapshotMetrics),
    [graphExpectations, snapshotMetrics],
  );
  const expectationRangeRows = useMemo(() => graphExpectationRangeRows(graphExpectations), [graphExpectations]);

  const snapshotCaseId = useMemo(() => {
    if (!snapshotJson || typeof snapshotJson !== "object") return null;
    const inner = snapshotJson.case;
    if (inner && typeof inner === "object" && inner.case_id != null) return String(inner.case_id);
    if (snapshotJson.case_id != null) return String(snapshotJson.case_id);
    return null;
  }, [snapshotJson]);

  const snapshotCaseIdMismatch =
    Boolean(snapshotCaseId) && Boolean(caseId) && snapshotCaseId !== String(caseId);

  const snapshotMetricsRoot = useMemo(() => {
    if (!snapshotJson || typeof snapshotJson !== "object") return null;
    const inner = snapshotJson.case;
    if (inner && typeof inner === "object" && inner.metrics != null) return inner.metrics;
    return snapshotJson.metrics ?? null;
  }, [snapshotJson]);

  const snapshotGoldFromFile = useMemo(() => {
    if (!snapshotJson || typeof snapshotJson !== "object") return null;
    return snapshotJson.gold ?? snapshotJson.case?.gold ?? null;
  }, [snapshotJson]);

  const onPickFile = (e) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    loadSnapshotFromFile(f);
  };

  return (
    <Box sx={{ mt: 2, display: "flex", flexDirection: "column", gap: 2 }}>
      <Typography sx={{ color: "rgba(255,255,255,0.6)", fontSize: "0.8125rem" }}>
        {t("benchmark.caseDialog.graphIntro")}
      </Typography>

      <CaseGraphExpectationsToolbar
        snapshotFileRef={snapshotFileRef}
        onPickFile={onPickFile}
        snapshotJson={snapshotJson}
        onClearSnapshot={clearSnapshot}
        onServerPreview={requestServerPreview}
        serverPreviewLoading={serverPreviewLoading}
        serverPreviewDisabled={!graphSnapshotApiFamily}
      />

      {snapshotLoadError ? (
        <Typography sx={{ color: "rgba(239,68,68,0.9)", fontSize: "0.8125rem" }} role="alert">
          {snapshotLoadError}
        </Typography>
      ) : null}

      {snapshotCaseIdMismatch ? (
        <Box
          sx={{
            border: "1px solid rgba(255,200,100,0.45)",
            borderRadius: 1.5,
            px: 1.5,
            py: 1,
            backgroundColor: "rgba(255,200,100,0.06)",
          }}
        >
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,200,100,0.95)" }}>
            {t("benchmark.caseDialog.snapshotCaseIdMismatch", {
              snapshotId: snapshotCaseId,
              dialogId: caseId,
            })}
          </Typography>
        </Box>
      ) : null}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "minmax(0,1fr) minmax(0,1fr)" },
          gap: 2,
          alignItems: "start",
        }}
      >
        <CaseGraphExpectationsGoldColumn
          graphExpectations={graphExpectations}
          graphExpectationsJson={graphExpectationsJson}
          expectationRangeRows={expectationRangeRows}
        />
        <CaseGraphExpectationsSnapshotColumn
          snapshotJson={snapshotJson}
          snapshotMetrics={snapshotMetrics}
          snapshotMetricsRoot={snapshotMetricsRoot}
          snapshotGoldFromFile={snapshotGoldFromFile}
        />
      </Box>

      <CaseGraphExpectationsCompareAndServer
        snapshotJson={snapshotJson}
        graphExpectationsJson={graphExpectationsJson}
        snapshotGoldFromFile={snapshotGoldFromFile}
        graphCompare={graphCompare}
        serverPreviewError={serverPreviewError}
        serverPreview={serverPreview}
      />
    </Box>
  );
}
