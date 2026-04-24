import React, { useEffect, useRef } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { useI18n } from "../../i18n/I18nContext.jsx";
import WorkPaperCard from "./WorkPaperCard.jsx";

/**
 * @param {{
 *   workspaceId: string,
 *   effectiveWorkIds: string[],
 *   papers: Map<string, any>,
 *   selectedWorkId: string,
 *   onCardActivate?: (workId: string) => void,
 * }} props
 */
export default function WorkspacePaperList({ workspaceId, effectiveWorkIds, papers, selectedWorkId, onCardActivate }) {
  const { t } = useI18n();
  const cardRefs = useRef({});
  const workIdsKey = effectiveWorkIds.join("|");

  useEffect(() => {
    if (!selectedWorkId) return undefined;
    const el = cardRefs.current[selectedWorkId];
    if (!el) return undefined;
    const raf = window.requestAnimationFrame(() => {
      el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
    return () => window.cancelAnimationFrame(raf);
  }, [selectedWorkId, workIdsKey]);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
      {workspaceId && effectiveWorkIds.length === 0 ? (
        <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("workspace.noPapers")}</Typography>
      ) : null}
      {effectiveWorkIds.map((wid) => {
        const row = papers.get(wid);
        return (
          <WorkPaperCard
            key={wid}
            workId={wid}
            title={row?.title || ""}
            year={row?.year}
            doi={row?.doi}
            arxivId={row?.arxivId}
            loading={row?.loading}
            error={row?.error}
            workspaceId={workspaceId}
            selected={Boolean(selectedWorkId) && wid === selectedWorkId}
            onCardActivate={onCardActivate}
            cardRef={(el) => {
              if (el) cardRefs.current[wid] = el;
              else delete cardRefs.current[wid];
            }}
          />
        );
      })}
    </Box>
  );
}
