import React, { useMemo, useCallback } from "react";
import { useTheme } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import { useI18n } from "../../../i18n/useI18n.js";
import CaseGraphExpectationsPanel from "./CaseGraphExpectationsPanel.jsx";

export default function CaseDetailFixtureTabs({
  open,
  caseId,
  family,
  graphSnapshotApiFamily,
  tabIdx,
  setTabIdx,
  detail,
  goldTabLabel,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const articlePreSx = useMemo(
    () => ({
      whiteSpace: "pre-wrap",
      wordBreak: "break-word",
      border: `1px solid ${tk.border.default}`,
      borderRadius: 2,
      padding: 2,
      maxHeight: 520,
      overflow: "auto",
      background: tk.control.outlinedBg,
      fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
      fontSize: "12px",
    }),
    [tk],
  );

  const jsonString = useMemo(() => {
    if (!detail?.gold) return "";
    return JSON.stringify(detail.gold, null, 2);
  }, [detail]);

  const graphExpectationsJson = useMemo(() => {
    const ge = detail?.gold?.graph_expectations;
    if (!ge) return "";
    return JSON.stringify(ge, null, 2);
  }, [detail]);

  const hasGraphTab = Boolean(graphExpectationsJson);
  const activeTabIdx = useMemo(() => {
    if (!hasGraphTab && tabIdx === 2) return 0;
    return Math.min(tabIdx, hasGraphTab ? 2 : 1);
  }, [hasGraphTab, tabIdx]);

  const onTabChange = useCallback(
    (e, v) => {
      setTabIdx(v);
    },
    [setTabIdx],
  );

  if (!detail) return null;

  return (
    <Box>
      <Tabs value={activeTabIdx} onChange={onTabChange}>
        <Tab label={t("benchmark.caseDialog.tabArticle")} />
        <Tab label={goldTabLabel} />
        {graphExpectationsJson ? <Tab label={t("benchmark.caseDialog.tabGraphExpectations")} /> : null}
      </Tabs>

      {activeTabIdx === 0 && (
        <Box sx={{ mt: 2 }}>
          <Typography sx={{ color: tk.text.secondary, mb: 1 }}>
            {t("benchmark.caseDialog.articlePreviewHint")}
          </Typography>
          <Box component="pre" sx={articlePreSx}>
            {detail.article_md}
          </Box>
        </Box>
      )}

      {activeTabIdx === 1 && (
        <Box sx={{ mt: 2 }}>
          <Typography sx={{ color: tk.text.secondary, mb: 1 }}>
            {t("benchmark.caseDialog.goldPayloadHint")}
          </Typography>
          <Accordion defaultExpanded={true}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography sx={{ fontWeight: 600 }}>{t("benchmark.caseDialog.accordionGold")}</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Box component="pre" sx={articlePreSx}>
                {jsonString}
              </Box>
            </AccordionDetails>
          </Accordion>
        </Box>
      )}

      {graphExpectationsJson && activeTabIdx === 2 && (
        <CaseGraphExpectationsPanel
          open={open}
          caseId={caseId}
          family={family}
          graphSnapshotApiFamily={graphSnapshotApiFamily}
          detail={detail}
        />
      )}
    </Box>
  );
}
