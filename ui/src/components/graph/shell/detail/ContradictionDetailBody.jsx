import React from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   t: (k: string, opts?: object) => string,
 *   selectedEdge: { raw?: object } | null,
 *   contradictionPayload: Record<string, unknown> | null,
 *   contradictionBusy: boolean,
 *   contradictionError: string,
 *   effectiveWorkspaceId: string,
 * }} props
 */
export default function ContradictionDetailBody({
  tk,
  t,
  selectedEdge,
  contradictionPayload,
  contradictionBusy,
  contradictionError,
  effectiveWorkspaceId,
}) {
  const edgeRaw =
    selectedEdge?.raw && typeof selectedEdge.raw === "object"
      ? /** @type {Record<string, unknown>} */ (selectedEdge.raw)
      : {};
  const edgeProps =
    edgeRaw.properties && typeof edgeRaw.properties === "object"
      ? /** @type {Record<string, unknown>} */ (edgeRaw.properties)
      : {};
  const pv =
    edgeRaw.contradiction_preview && typeof edgeRaw.contradiction_preview === "object"
      ? /** @type {Record<string, unknown>} */ (edgeRaw.contradiction_preview)
      : {};
  const rel =
    contradictionPayload?.relationship && typeof contradictionPayload.relationship === "object"
      ? /** @type {Record<string, unknown>} */ (contradictionPayload.relationship)
      : {};
  const underspecified = Boolean(pv.underspecified ?? rel.underspecified ?? edgeProps.underspecified);
  const subtype = String(pv.subtype || rel.subtype || edgeProps.subtype || "").trim();
  const severity = String(pv.severity || rel.severity || edgeProps.severity || "").trim();
  const provenance = String(pv.provenance || rel.provenance || edgeProps.provenance || "").trim();
  const quoteADisplay = String(rel.quote_a || edgeProps.quote_a_preview || "").trim();
  const quoteBDisplay = String(rel.quote_b || edgeProps.quote_b_preview || "").trim();
  const claimAText = String(rel.claim_a_text || edgeProps.claim_a_text || "").trim();
  const claimBText = String(rel.claim_b_text || edgeProps.claim_b_text || "").trim();

  return (
    <>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mb: 1 }}>
        {subtype ? <Chip size="small" label={`${t("graph.detailPanel.contradictionSubtype")}: ${subtype}`} /> : null}
        {severity ? <Chip size="small" label={`${t("graph.detailPanel.contradictionSeverity")}: ${severity}`} /> : null}
        {provenance ? <Chip size="small" label={`${t("graph.detailPanel.contradictionProvenance")}: ${provenance}`} /> : null}
      </Box>
      {underspecified ? (
        <Alert severity="warning" sx={{ mb: 1, py: 0.5 }}>
          {t("graph.detailPanel.contradictionUnderspecified")}
        </Alert>
      ) : null}
      {!effectiveWorkspaceId ? (
        <Alert severity="info" sx={{ mb: 1, py: 0.5 }}>
          {t("graph.detailPanel.contradictionNoWorkspace")}
        </Alert>
      ) : null}
      {contradictionBusy ? (
        <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted }}>{t("graph.detailPanel.contradictionLoading")}</Typography>
      ) : null}
      {contradictionError ? (
        <Alert severity="error" sx={{ mt: 0.75, py: 0.5 }}>
          {contradictionError}
        </Alert>
      ) : null}
      {claimAText || claimBText ? (
        <Box sx={{ mt: 1 }}>
          {claimAText ? (
            <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, mb: 0.25 }}>
              {t("graph.detailPanel.contradictionClaimA")}
            </Typography>
          ) : null}
          {claimAText ? (
            <Typography sx={{ fontSize: "0.78rem", color: tk.text.primary, mb: 1, lineHeight: 1.45 }}>{claimAText}</Typography>
          ) : null}
          {claimBText ? (
            <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, mb: 0.25 }}>
              {t("graph.detailPanel.contradictionClaimB")}
            </Typography>
          ) : null}
          {claimBText ? (
            <Typography sx={{ fontSize: "0.78rem", color: tk.text.primary, mb: 1, lineHeight: 1.45 }}>{claimBText}</Typography>
          ) : null}
        </Box>
      ) : null}
      {quoteADisplay || quoteBDisplay ? (
        <Box sx={{ mt: 0.5 }}>
          {quoteADisplay ? (
            <>
              <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, mb: 0.25 }}>
                {t("graph.detailPanel.contradictionQuoteA")}
              </Typography>
              <Typography
                component="div"
                sx={{
                  fontSize: "0.75rem",
                  color: tk.text.primary,
                  mb: 1,
                  lineHeight: 1.45,
                  whiteSpace: "pre-wrap",
                  borderLeft: `2px solid ${tk.border.strong}`,
                  pl: 1,
                }}
              >
                {quoteADisplay}
              </Typography>
            </>
          ) : null}
          {quoteBDisplay ? (
            <>
              <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, mb: 0.25 }}>
                {t("graph.detailPanel.contradictionQuoteB")}
              </Typography>
              <Typography
                component="div"
                sx={{
                  fontSize: "0.75rem",
                  color: tk.text.primary,
                  mb: 0.5,
                  lineHeight: 1.45,
                  whiteSpace: "pre-wrap",
                  borderLeft: `2px solid ${tk.border.strong}`,
                  pl: 1,
                }}
              >
                {quoteBDisplay}
              </Typography>
            </>
          ) : null}
        </Box>
      ) : null}
      {rel.rationale_short || edgeProps.rationale_short ? (
        <Box sx={{ mt: 0.5 }}>
          <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, mb: 0.25 }}>
            {t("graph.detailPanel.contradictionRationale")}
          </Typography>
          <Typography sx={{ fontSize: "0.78rem", color: tk.text.primary, lineHeight: 1.45 }}>
            {String(rel.rationale_short || edgeProps.rationale_short || "")}
          </Typography>
        </Box>
      ) : null}
    </>
  );
}
