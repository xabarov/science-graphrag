import React from "react";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import ArticleOutlinedIcon from "@mui/icons-material/ArticleOutlined";
import OpenInNewOutlinedIcon from "@mui/icons-material/OpenInNewOutlined";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import { Link as RouterLink } from "react-router-dom";

import { GRAPH_PATH, READER_PATH } from "../../../../routes/paths.js";
import { buildStandaloneTracePath } from "../../traceability/traceabilityState.js";
import { CursorIconButton, CursorSmallButton } from "../../../common/index.js";
import { CitationBodyExpandable } from "./CitationBodyExpandable.jsx";
import { citationRankFromRow, citationTraceExtras, deriveSourceListPresentation } from "./askSourcePresentation.js";
import { formatCitationHeadline, pickCitationWorkTitle } from "./citationDisplay.js";
import { pickCitationBodyText } from "./citationBodyText.js";

/**
 * Structured citations / found papers list for Ask answer panel.
 *
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   citations: Record<string, unknown>[],
 *   answerClass: string,
 *   workspaceId?: string,
 *   isRunActive?: boolean,
 *   hideStructuredCitations?: boolean,
 *   chatDetailLevel?: "simple" | "detailed",
 * }} props
 */
export function AskSourceList({
  t,
  citations,
  answerClass,
  workspaceId = "",
  isRunActive = false,
  hideStructuredCitations = false,
  chatDetailLevel = "simple",
}) {
  const tk = useTheme().appTokens;
  const { citationListLabelKey, allPassagesMissing, somePassagesMissing, suppressMissingPassageChrome } =
    deriveSourceListPresentation(answerClass, citations);

  if (hideStructuredCitations) return null;
  if (isRunActive && citations.length === 0) return null;

  return (
    <>
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.5, color: tk.text.primary }}>
        {t(citationListLabelKey)}
      </Typography>
      {allPassagesMissing ? (
        <Alert severity="info" sx={{ mb: 1, fontSize: "0.75rem", backgroundColor: tk.surface.panelAlt }}>
          {t("askPanel.citation.noSnippetBulkAll")}
        </Alert>
      ) : somePassagesMissing ? (
        <Alert severity="info" sx={{ mb: 1, fontSize: "0.75rem", backgroundColor: tk.surface.panelAlt }}>
          {t("askPanel.citation.noSnippetBulkPartial")}
        </Alert>
      ) : null}
      {citations.length === 0 ? (
        <Typography sx={{ fontSize: "0.8125rem", color: tk.text.secondary }}>{t("askPanel.citations.none")}</Typography>
      ) : (
        citations.map((c, i) => {
          const wid = c.work_id != null ? String(c.work_id) : "";
          const extUrl = c.url != null ? String(c.url).trim() : "";
          const isWebSource =
            String(c.source_type || "").toLowerCase() === "web" ||
            (Boolean(extUrl) &&
              /^https?:\/\//i.test(extUrl) &&
              !String(wid).trim());
          const chunkFingerprint = c.chunk_fingerprint != null ? String(c.chunk_fingerprint) : "";
          const sectionPath = c.section_path != null ? String(c.section_path) : "";
          const citationIndex = String(i + 1);
          const rank = citationRankFromRow(c, i);
          const traceExtras = citationTraceExtras(workspaceId, chunkFingerprint, sectionPath, citationIndex);
          const readerUrl = wid ? buildStandaloneTracePath(READER_PATH, wid, traceExtras) : "";
          const graphUrl = wid ? buildStandaloneTracePath(GRAPH_PATH, wid, traceExtras) : "";
          const workTitle = pickCitationWorkTitle(c);
          const hasPassage = Boolean(pickCitationBodyText(c).trim());
          const suppressMissingPlaceholder =
            !hasPassage && (suppressMissingPassageChrome || allPassagesMissing || somePassagesMissing);
          const showWorkIdSecondary = chatDetailLevel === "detailed" && Boolean(wid.trim());
          const doiStr = c.doi != null ? String(c.doi).trim() : "";
          const showDoiSecondary = chatDetailLevel === "detailed" && Boolean(doiStr) && isWebSource;
          const deepLinks = isWebSource && extUrl
            ? chatDetailLevel === "detailed"
              ? (
                  <Tooltip title={t("askPanel.citation.tooltipWebSource")}>
                    <CursorSmallButton
                      component="a"
                      href={extUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={t("askPanel.citation.tooltipWebSource")}
                      sx={{ textTransform: "none", minWidth: 0, px: 1.1 }}
                    >
                      {t("askPanel.citation.linkWeb")}
                    </CursorSmallButton>
                  </Tooltip>
                )
              : (
                  <Tooltip title={t("askPanel.citation.tooltipWebSource")}>
                    <CursorIconButton
                      component="a"
                      href={extUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={t("askPanel.citation.tooltipWebSource")}
                      size="small"
                    >
                      <OpenInNewOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                    </CursorIconButton>
                  </Tooltip>
                )
            : wid
              ? chatDetailLevel === "detailed"
                ? (
                    <>
                      <Tooltip title={t("askPanel.citation.tooltipArticle")}>
                        <CursorSmallButton
                          component={RouterLink}
                          to={readerUrl}
                          aria-label={t("askPanel.citation.tooltipArticle")}
                          sx={{ textTransform: "none", minWidth: 0, px: 1.1 }}
                        >
                          {t("askPanel.citation.linkReader")}
                        </CursorSmallButton>
                      </Tooltip>
                      <Tooltip title={t("askPanel.citation.tooltipGraphWork")}>
                        <CursorSmallButton
                          component={RouterLink}
                          to={graphUrl}
                          aria-label={t("askPanel.citation.tooltipGraphWork")}
                          sx={{ textTransform: "none", minWidth: 0, px: 1.1 }}
                        >
                          {t("askPanel.citation.linkGraph")}
                        </CursorSmallButton>
                      </Tooltip>
                    </>
                  )
                : (
                    <>
                      <Tooltip title={t("askPanel.citation.tooltipArticle")}>
                        <CursorIconButton
                          component={RouterLink}
                          to={readerUrl}
                          aria-label={t("askPanel.citation.tooltipArticle")}
                          size="small"
                        >
                          <ArticleOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                        </CursorIconButton>
                      </Tooltip>
                      <Tooltip title={t("askPanel.citation.tooltipGraphWork")}>
                        <CursorIconButton
                          component={RouterLink}
                          to={graphUrl}
                          aria-label={t("askPanel.citation.tooltipGraphWork")}
                          size="small"
                        >
                          <AccountTreeOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                        </CursorIconButton>
                      </Tooltip>
                    </>
                  )
              : null;
          return (
            <Box
              key={wid ? `${wid}-${i}` : extUrl ? `${extUrl}-${i}` : `citation-${i}`}
              id={`ask-citation-${i + 1}`}
              data-testid={`citation-block-${i}`}
              sx={{ mb: 1.25, fontSize: "0.8125rem", color: tk.text.secondary }}
            >
              <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, fontWeight: 600 }}>
                {formatCitationHeadline({
                  rank,
                  citation: c,
                  chatDetailLevel,
                  t,
                })}
              </Typography>
              {workTitle ? (
                <Typography
                  sx={{
                    fontSize: "0.75rem",
                    color: tk.text.muted,
                    mt: 0.15,
                    lineHeight: 1.35,
                  }}
                >
                  {t("askPanel.citation.sourceLine", { title: workTitle })}
                </Typography>
              ) : null}
              {showWorkIdSecondary ? (
                <Typography
                  sx={{ fontSize: "0.68rem", color: tk.text.faint, mt: 0.25, fontFamily: "monospace", wordBreak: "break-all" }}
                >
                  {t("askPanel.citation.workIdLine", { id: wid })}
                </Typography>
              ) : null}
              {showDoiSecondary ? (
                <Typography
                  sx={{ fontSize: "0.68rem", color: tk.text.faint, mt: 0.25, fontFamily: "monospace", wordBreak: "break-all" }}
                >
                  DOI: {doiStr}
                </Typography>
              ) : null}
              <CitationBodyExpandable
                t={t}
                citation={c}
                defaultExpanded
                suppressMissingPlaceholder={suppressMissingPlaceholder}
                trailingActions={deepLinks || null}
              />
              {chatDetailLevel === "detailed" && String(c.chunk_fingerprint ?? "").trim() !== "" ? (
                <Typography
                  data-testid={`citation-chunk-fingerprint-${i}`}
                  sx={{ fontSize: "0.75rem", color: tk.text.muted, mt: 0.35 }}
                >
                  {t("askPanel.chunkLabel")} {String(c.chunk_fingerprint).trim()}
                </Typography>
              ) : null}
            </Box>
          );
        })
      )}
    </>
  );
}
