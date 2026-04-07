import React, { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { listBenchmarkModels } from "../../services/benchmarkApi.js";

export default function BenchmarkModelSelector({
  family = "layer1",
  value,
  customModelId,
  onChange,
  onCustomModelIdChange,
}) {
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const resp = await listBenchmarkModels();
        if (!cancelled) setPayload(resp);
      } catch (e) {
        if (!cancelled) setError(e?.message || "failed_to_load_models");
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const items = useMemo(() => {
    const allItems = payload?.items || [];
    return allItems.filter((item) => (item.family_support || []).includes(family));
  }, [family, payload]);

  const selected = items.find((item) => item.profile_id === value) || null;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Select
        size="small"
        value={value || "env_default"}
        onChange={(e) => onChange?.(e.target.value, items.find((item) => item.profile_id === e.target.value))}
      >
        {items.map((item) => (
          <MenuItem key={item.profile_id} value={item.profile_id}>
            {item.label}
          </MenuItem>
        ))}
      </Select>

      {selected?.supports_custom_model_id ? (
        <TextField
          size="small"
          label="Custom model id"
          value={customModelId || ""}
          onChange={(e) => onCustomModelIdChange?.(e.target.value)}
        />
      ) : null}

      {selected ? (
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.6)" }}>
          role: {selected.role} | model: {selected.model_id || "from environment"}
        </Typography>
      ) : null}

      {error ? (
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(239, 68, 68, 0.9)" }}>{error}</Typography>
      ) : null}
    </Box>
  );
}
