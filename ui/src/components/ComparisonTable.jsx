import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

function _uniq(arr) {
  return Array.from(new Set(arr.filter(Boolean)));
}

function _listPreview(list, max = 6) {
  if (!Array.isArray(list)) return [];
  return list.slice(0, max);
}

export default function ComparisonTable({ predicted, gold }) {
  const pWork = predicted?.work_metadata || {};
  const gWork = gold?.work_metadata || {};

  const pAuthorships = Array.isArray(predicted?.authorships) ? predicted.authorships : [];
  const gAuthorships = Array.isArray(gold?.authorships) ? gold.authorships : [];

  const pRefs = Array.isArray(predicted?.references) ? predicted.references : [];
  const gRefs = gold?.references || {};

  const extractedArxivIds = _uniq(pRefs.map((r) => r?.arxiv_id));
  const extractedDoi = _uniq(pRefs.map((r) => r?.doi));
  const goldSampleArxiv = Array.isArray(gRefs?.sample_arxiv_ids) ? gRefs.sample_arxiv_ids : [];
  const goldSampleDoi = Array.isArray(gRefs?.sample_dois) ? gRefs.sample_dois : [];

  return (
    <Box sx={{ border: "1px solid rgba(255, 255, 255, 0.08)", borderRadius: 2, p: 2 }}>
      <Typography sx={{ fontWeight: 600, mb: 1 }}>Comparison (Predicted vs Gold)</Typography>

      <Box sx={{ mb: 2 }}>
        <Typography sx={{ color: "rgba(255,255,255,0.7)", fontWeight: 600 }}>Work metadata</Typography>
        <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, mt: 1 }}>
          {[
            ["Title", pWork?.title, gWork?.title],
            ["Publication year", pWork?.publication_year, gWork?.publication_year],
            ["DOI", pWork?.doi, gWork?.doi],
            ["arXiv ID", pWork?.arxiv_id, gWork?.arxiv_id],
            ["Work type", pWork?.work_type, gWork?.work_type],
          ].map(([label, pv, gv]) => (
            <React.Fragment key={label}>
              <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>{label} (pred)</Typography>
              <Typography sx={{ wordBreak: "break-word" }}>{pv ?? "-"}</Typography>
              <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>{label} (gold)</Typography>
              <Typography sx={{ wordBreak: "break-word" }}>{gv ?? "-"}</Typography>
            </React.Fragment>
          ))}
        </Box>
      </Box>

      <Box sx={{ mb: 2 }}>
        <Typography sx={{ color: "rgba(255,255,255,0.7)", fontWeight: 600 }}>Authorships</Typography>
        <Typography sx={{ mt: 0.5, color: "rgba(255,255,255,0.6)" }}>
          Predicted: {pAuthorships.length} / Gold: {gAuthorships.length}
        </Typography>
        <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, mt: 1 }}>
          <Box>
            <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>Predicted names</Typography>
            <Typography sx={{ wordBreak: "break-word" }}>
              {_listPreview(pAuthorships.map((a) => a?.author_raw_name)).join(", ") || "-"}
            </Typography>
          </Box>
          <Box>
            <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>Gold names</Typography>
            <Typography sx={{ wordBreak: "break-word" }}>
              {_listPreview(gAuthorships.map((a) => a?.name)).join(", ") || "-"}
            </Typography>
          </Box>
        </Box>
      </Box>

      <Box>
        <Typography sx={{ color: "rgba(255,255,255,0.7)", fontWeight: 600 }}>References</Typography>
        <Typography sx={{ mt: 0.5, color: "rgba(255,255,255,0.6)" }}>
          Predicted: {pRefs.length} / Gold expected_count: {gRefs?.expected_count ?? "-"} (min {gRefs?.min_count ?? "-"})
        </Typography>

        <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, mt: 1 }}>
          <Box>
            <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>Sample arXiv (pred)</Typography>
            <Typography sx={{ wordBreak: "break-word" }}>
              {_listPreview(extractedArxivIds).join(", ") || "-"}
            </Typography>
          </Box>
          <Box>
            <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>Sample arXiv (gold)</Typography>
            <Typography sx={{ wordBreak: "break-word" }}>
              {_listPreview(goldSampleArxiv).join(", ") || "-"}
            </Typography>
          </Box>

          <Box>
            <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>Sample DOI (pred)</Typography>
            <Typography sx={{ wordBreak: "break-word" }}>
              {_listPreview(extractedDoi).join(", ") || "-"}
            </Typography>
          </Box>
          <Box>
            <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>Sample DOI (gold)</Typography>
            <Typography sx={{ wordBreak: "break-word" }}>
              {_listPreview(goldSampleDoi).join(", ") || "-"}
            </Typography>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

