import React, { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
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
  onModelsLoaded,
}) {
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const resp = await listBenchmarkModels();
        if (!cancelled) {
          setPayload(resp);
          onModelsLoaded?.(resp?.items || []);
        }
      } catch (e) {
        if (!cancelled) setError(e?.message || "failed_to_load_models");
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [onModelsLoaded]);

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
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
          <Box sx={{ display: "flex", gap: 0.75, flexWrap: "wrap" }}>
            <Chip size="small" label={`role: ${selected.role || "generic"}`} variant="outlined" />
            <Chip size="small" label={`model: ${selected.model_id || "from environment"}`} variant="outlined" />
            <Chip
              size="small"
              label={`gold: ${selected.default_gold_source || (family === "layer2" ? "semantic_gold" : "curated_gold")}`}
              variant="outlined"
            />
            <Chip
              size="small"
              label={`threshold: ${selected.default_threshold_profile || "from_gold"}`}
              variant="outlined"
            />
          </Box>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.6)" }}>
            {selected.supports_custom_model_id
              ? "This profile supports overriding the model id."
              : "This profile uses its preset or environment-backed model id."}
          </Typography>
        </Box>
      ) : null}

      {error ? (
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(239, 68, 68, 0.9)" }}>{error}</Typography>
      ) : null}
    </Box>
  );
}
