import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

function _names(list, key = "name") {
  if (!Array.isArray(list)) return [];
  return list.map((x) => (x && x[key] ? String(x[key]) : "")).filter(Boolean);
}

function _normSet(items) {
  return new Set(items.map((x) => String(x).trim().toLowerCase()).filter(Boolean));
}

export default function SemanticComparisonTable({ predicted, gold }) {
  const pMethods = _names(predicted?.methods);
  const pDatasets = _names(predicted?.datasets);
  const gMethods = Array.isArray(gold?.expected_method_names_normalized) ? gold.expected_method_names_normalized : [];
  const gDatasets = Array.isArray(gold?.expected_dataset_names_normalized)
    ? gold.expected_dataset_names_normalized
    : [];

  const pm = _normSet(pMethods);
  const gm = _normSet(gMethods);
  const pd = _normSet(pDatasets);
  const gd = _normSet(gDatasets);
  const methodsTp = [...pm].filter((x) => gm.has(x)).length;
  const datasetsTp = [...pd].filter((x) => gd.has(x)).length;

  return (
    <Box sx={{ border: "1px solid rgba(255, 255, 255, 0.08)", borderRadius: 2, p: 2 }}>
      <Typography sx={{ fontWeight: 600, mb: 1 }}>Semantic (methods / datasets)</Typography>

      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)", mb: 1 }}>
        Normalized overlap: methods {methodsTp}/{gm.size || 0} gold matched in pred; datasets {datasetsTp}/{gd.size || 0}{" "}
        gold matched in pred (quick diff view, not official benchmark metric).
      </Typography>

      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, mb: 2 }}>
        <Box>
          <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>Predicted methods</Typography>
          <Typography sx={{ wordBreak: "break-word" }}>{pMethods.join(", ") || "—"}</Typography>
        </Box>
        <Box>
          <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>Gold methods (normalized)</Typography>
          <Typography sx={{ wordBreak: "break-word" }}>{gMethods.join(", ") || "—"}</Typography>
        </Box>
        <Box>
          <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>Predicted datasets</Typography>
          <Typography sx={{ wordBreak: "break-word" }}>{pDatasets.join(", ") || "—"}</Typography>
        </Box>
        <Box>
          <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>Gold datasets (normalized)</Typography>
          <Typography sx={{ wordBreak: "break-word" }}>{gDatasets.join(", ") || "—"}</Typography>
        </Box>
      </Box>

      {predicted?.extraction_notes ? (
        <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem" }}>
          Notes: {predicted.extraction_notes}
        </Typography>
      ) : null}
    </Box>
  );
}
