import React, { useEffect, useRef } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../i18n/useI18n.js";
import WorkspacePaperRow from "./WorkspacePaperRow.jsx";

/**
 * @param {{
 *   workspaceId: string,
 *   effectiveWorkIds: string[],
 *   papers: Map<string, any>,
 *   selectedWorkId: string,
 *   onRowActivate?: (workId: string) => void,
 *   onRemoveWork?: (workId: string) => void,
 * }} props
 */
export default function WorkspacePaperList({
  workspaceId,
  effectiveWorkIds,
  papers,
  selectedWorkId,
  onRowActivate,
  onRemoveWork,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const rowRefs = useRef({});
  const workIdsKey = effectiveWorkIds.join("|");

  useEffect(() => {
    if (!selectedWorkId) return undefined;
    const el = rowRefs.current[selectedWorkId];
    if (!el) return undefined;
    const raf = window.requestAnimationFrame(() => {
      el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
    return () => window.cancelAnimationFrame(raf);
  }, [selectedWorkId, workIdsKey]);

  return (
    <Box
      sx={{
        borderRadius: "6px",
        border: `1px solid ${tk.border.default}`,
        backgroundColor: tk.surface.sidebar,
        overflow: "hidden",
      }}
    >
      {workspaceId && effectiveWorkIds.length === 0 ? (
        <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted, p: 1.5 }}>{t("workspace.noPapers")}</Typography>
      ) : null}
      {effectiveWorkIds.map((wid) => {
        const row = papers.get(wid);
        return (
          <WorkspacePaperRow
            key={wid}
            workspaceId={workspaceId}
            workId={wid}
            title={row?.title || ""}
            year={row?.year}
            doi={row?.doi}
            arxivId={row?.arxivId}
            loading={row?.loading}
            error={row?.error}
            selected={Boolean(selectedWorkId) && wid === selectedWorkId}
            onRowActivate={onRowActivate}
            onRemoveWork={onRemoveWork}
            rowRef={(el) => {
              if (el) rowRefs.current[wid] = el;
              else delete rowRefs.current[wid];
            }}
          />
        );
      })}
    </Box>
  );
}
