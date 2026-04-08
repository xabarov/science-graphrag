import React, { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { getHealth, getWorks } from "../services/researchApi.js";

/** Lightweight read-only probes for the admin hub (no secrets). */
export default function AdminApiStatusStrip() {
  const [row, setRow] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const out = { healthLabel: "—", worksLabel: "—" };
      try {
        const h = await getHealth();
        if (!cancelled) {
          out.healthLabel = h.data?.status === "ok" ? "OK" : JSON.stringify(h.data);
        }
      } catch {
        if (!cancelled) out.healthLabel = "unreachable";
      }
      try {
        const w = await getWorks({ limit: 1, offset: 0 });
        if (!cancelled) {
          const t = w.data?.total;
          out.worksLabel = Number.isFinite(Number(t)) ? `catalog total ${t}` : "reachable";
        }
      } catch {
        if (!cancelled) out.worksLabel = "unreachable";
      }
      if (!cancelled) setRow(out);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!row) {
    return (
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mb: 2 }}>
        Loading API status…
      </Typography>
    );
  }

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" },
        gap: 1,
        mb: 2,
      }}
      role="status"
      aria-live="polite"
    >
      <Box
        sx={{
          p: 1.25,
          borderRadius: "6px",
          border: "1px solid rgba(255,255,255,0.08)",
          backgroundColor: "#141414",
        }}
      >
        <Typography sx={{ fontSize: "0.6875rem", color: "rgba(255,255,255,0.45)", mb: 0.5 }}>GET /health</Typography>
        <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)", fontFamily: "monospace" }}>{row.healthLabel}</Typography>
      </Box>
      <Box
        sx={{
          p: 1.25,
          borderRadius: "6px",
          border: "1px solid rgba(255,255,255,0.08)",
          backgroundColor: "#141414",
        }}
      >
        <Typography sx={{ fontSize: "0.6875rem", color: "rgba(255,255,255,0.45)", mb: 0.5 }}>GET /v1/works</Typography>
        <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)", fontFamily: "monospace" }}>{row.worksLabel}</Typography>
      </Box>
    </Box>
  );
}
