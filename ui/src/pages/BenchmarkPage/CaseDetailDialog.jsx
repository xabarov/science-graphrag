import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Dialog from "@mui/material/Dialog";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";

import { CursorButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import CaseDetailArtifactsSection from "./caseDetail/CaseDetailArtifactsSection.jsx";
import CaseDetailFixtureTabs from "./caseDetail/CaseDetailFixtureTabs.jsx";
import CaseDetailStatusSection from "./caseDetail/CaseDetailStatusSection.jsx";
import { useCaseDetailDialogData } from "./caseDetail/useCaseDetailDialogData.js";
import { getCaseDetailFamilyConfig } from "./families/registry.js";

export default function CaseDetailDialog({ open, caseId, family = "layer1", onClose }) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("sm"));
  const navigate = useNavigate();
  const { t } = useI18n();
  const [tabIdx, setTabIdx] = useState(0);

  const familyConfig = useMemo(() => getCaseDetailFamilyConfig(family), [family]);

  const { detail, artifacts, goldSource, setGoldSource, loading, error } = useCaseDetailDialogData({
    open,
    caseId,
    family,
    usesLayer1Gold: familyConfig.usesLayer1Gold,
    onDetailFetchStart: () => setTabIdx(0),
  });

  const graphExpectationsJson = useMemo(() => {
    const ge = detail?.gold?.graph_expectations;
    if (!ge) return "";
    return JSON.stringify(ge, null, 2);
  }, [detail]);

  const displayTabIdx = useMemo(() => {
    if (detail && tabIdx === 2 && !graphExpectationsJson) return 0;
    return tabIdx;
  }, [detail, graphExpectationsJson, tabIdx]);

  const goldTabLabel =
    familyConfig.usesLayer1Gold && goldSource === "teacher_gold"
      ? t("benchmark.caseDialog.tabGoldTeacher")
      : t("benchmark.caseDialog.tabGoldCurated");

  const familyExtras = familyConfig.renderCaseDetailExtras?.({
    detail,
    artifacts,
    caseId,
    family,
    navigate,
    onClose,
  });

  return (
    <Dialog
      open={open}
      onClose={onClose}
      fullWidth
      maxWidth="lg"
      fullScreen={fullScreen}
      aria-labelledby="benchmark-case-dialog-title"
    >
      <DialogTitle id="benchmark-case-dialog-title">
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1 }}>
          <Box>
            <Typography sx={{ fontWeight: 700 }}>{t("benchmark.caseDialog.title")}</Typography>
            <Typography sx={{ color: "rgba(255,255,255,0.6)", fontSize: "0.8125rem" }}>
              {t("benchmark.caseDialog.subtitleCaseId", { id: caseId || "-" })}
            </Typography>
          </Box>
          <CursorButton onClick={onClose} aria-label={t("benchmark.caseDialog.closeAriaLabel")}>
            {t("benchmark.caseDialog.close")}
          </CursorButton>
        </Box>
      </DialogTitle>
      <DialogContent dividers>
        <CaseDetailStatusSection error={error} loading={loading} />

        <CaseDetailArtifactsSection
          artifacts={artifacts}
          usesLayer1Gold={familyConfig.usesLayer1Gold}
          goldSource={goldSource}
          onGoldSourceChange={setGoldSource}
          onClose={onClose}
        />

        {familyExtras ?? null}

        <CaseDetailFixtureTabs
          open={open}
          caseId={caseId}
          family={family}
          graphSnapshotApiFamily={familyConfig.graphSnapshotApiFamily}
          tabIdx={displayTabIdx}
          setTabIdx={setTabIdx}
          detail={detail}
          goldTabLabel={goldTabLabel}
        />
      </DialogContent>
    </Dialog>
  );
}
