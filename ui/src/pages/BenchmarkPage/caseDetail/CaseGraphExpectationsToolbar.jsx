import React from "react";
import Box from "@mui/material/Box";

import { CursorSmallButton } from "../../../components/common/index.js";
import { useI18n } from "../../../i18n/useI18n.js";

export default function CaseGraphExpectationsToolbar({
  snapshotFileRef,
  onPickFile,
  snapshotJson,
  onClearSnapshot,
  onServerPreview,
  serverPreviewLoading,
  serverPreviewDisabled,
}) {
  const { t } = useI18n();

  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
      <input
        ref={snapshotFileRef}
        type="file"
        accept="application/json,.json"
        style={{ display: "none" }}
        onChange={onPickFile}
      />
      <CursorSmallButton onClick={() => snapshotFileRef.current?.click()}>
        {t("benchmark.caseDialog.loadSnapshotJson")}
      </CursorSmallButton>
      {snapshotJson ? (
        <>
          <CursorSmallButton onClick={onClearSnapshot}>{t("benchmark.caseDialog.clearSnapshot")}</CursorSmallButton>
          <CursorSmallButton onClick={onServerPreview} disabled={serverPreviewLoading || serverPreviewDisabled}>
            {serverPreviewLoading
              ? t("benchmark.caseDialog.previewOnServerLoading")
              : t("benchmark.caseDialog.previewOnServer")}
          </CursorSmallButton>
        </>
      ) : null}
    </Box>
  );
}
