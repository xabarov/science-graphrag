import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

function _toFloat(x) {
  const v = Number(x);
  return Number.isFinite(v) ? v : 0;
}

export default function MetricsCard({ metrics }) {
  const passed = Boolean(metrics?.contract?.passed);
  const checks = metrics?.contract?.checks || {};

  const namesF1 = _toFloat(metrics?.authorships?.names_f1);
  const sampleArxivF1 = _toFloat(metrics?.references?.sample_arxiv_f1);
  const sampleDoiF1 = _toFloat(metrics?.references?.sample_doi_f1);

  const borderColor = passed ? "rgba(99, 102, 241, 0.35)" : "rgba(239, 68, 68, 0.35)";
  const bg = passed ? "rgba(99, 102, 241, 0.08)" : "rgba(239, 68, 68, 0.06)";

  return (
    <Box
      sx={{
        border: "1px solid rgba(255, 255, 255, 0.08)",
        borderRadius: 2,
        padding: 1.5,
        backgroundColor: bg,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Typography sx={{ fontWeight: 600 }}>Contract</Typography>
        <Box
          sx={{
            border: `1px solid ${borderColor}`,
            backgroundColor: bg,
            borderRadius: 999,
            padding: "4px 10px",
          }}
        >
          <Typography sx={{ color: passed ? "rgba(129, 140, 248, 0.95)" : "rgba(239, 68, 68, 0.8)" }}>
            {passed ? "PASS" : "FAIL"}
          </Typography>
        </Box>
      </Box>

      <Box sx={{ display: "flex", gap: 2, mt: 1 }}>
        <Box>
          <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>Authorships names_f1</Typography>
          <Typography sx={{ fontWeight: 600 }}>{namesF1.toFixed(3)}</Typography>
        </Box>
        <Box>
          <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>References sample_arxiv_f1</Typography>
          <Typography sx={{ fontWeight: 600 }}>{sampleArxivF1.toFixed(3)}</Typography>
        </Box>
        <Box>
          <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>References sample_doi_f1</Typography>
          <Typography sx={{ fontWeight: 600 }}>{sampleDoiF1.toFixed(3)}</Typography>
        </Box>
      </Box>

      {checks && Object.keys(checks).length > 0 && (
        <Typography sx={{ mt: 1, color: "rgba(255,255,255,0.6)" }}>
          Checks:{" "}
          {Object.entries(checks)
            .slice(0, 5)
            .map(([k, v]) => `${k}=${v}`)
            .join(", ")}
        </Typography>
      )}
    </Box>
  );
}

