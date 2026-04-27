import React from "react";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormGroup from "@mui/material/FormGroup";
import Radio from "@mui/material/Radio";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

function ScopeCard({ title, subtitle, active, children, onClick }) {
  const tk = useTheme().appTokens;
  return (
    <Box
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onClick?.();
      }}
      sx={{
        border: `1px solid ${tk.border.default}`,
        borderRadius: 1.5,
        backgroundColor: active ? tk.accent.chipReadyBg : tk.surface.panel,
        padding: 1.25,
        cursor: "pointer",
        minHeight: 120,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1 }}>
        <Box>
          <Typography sx={{ fontWeight: 600 }}>{title}</Typography>
          <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted }}>{subtitle}</Typography>
        </Box>
        <Radio checked={active} size="small" />
      </Box>
      {children}
    </Box>
  );
}

export default function BenchmarkRunScopeSelector({
  mergeSafeCases,
  nightlyCases,
  nightlyLabel,
  loadingCases,
  selectedCaseIds,
  launcherScope,
  onScopeChange,
  onToggleCase,
}) {
  const tk = useTheme().appTokens;
  const selectedSet = new Set(selectedCaseIds || []);
  return (
    <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2 }}>
      <ScopeCard
        title="Selected cases"
        subtitle={`${selectedCaseIds.length || 0} selected`}
        active={launcherScope === "selected"}
        onClick={() => onScopeChange?.("selected")}
      >
        <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2 }}>
          <Box>
            <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, mb: 0.5 }}>
              merge_safe
            </Typography>
            <Typography sx={{ color: tk.text.muted, fontSize: "0.75rem", mb: 0.5 }}>
              {loadingCases ? "loading..." : `${mergeSafeCases.length} cases`}
            </Typography>
            <FormGroup>
              {mergeSafeCases.map((item) => (
                <FormControlLabel
                  key={item.case_id}
                  control={
                    <Checkbox
                      size="small"
                      checked={selectedSet.has(item.case_id)}
                      onChange={() => onToggleCase?.(item.case_id)}
                    />
                  }
                  label={item.case_id}
                />
              ))}
            </FormGroup>
          </Box>
          <Box>
            <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, mb: 0.5 }}>
              {nightlyLabel}
            </Typography>
            <Typography sx={{ color: tk.text.muted, fontSize: "0.75rem", mb: 0.5 }}>
              {loadingCases ? "loading..." : `${nightlyCases.length} cases`}
            </Typography>
            <FormGroup>
              {nightlyCases.map((item) => (
                <FormControlLabel
                  key={item.case_id}
                  control={
                    <Checkbox
                      size="small"
                      checked={selectedSet.has(item.case_id)}
                      onChange={() => onToggleCase?.(item.case_id)}
                    />
                  }
                  label={item.case_id}
                />
              ))}
            </FormGroup>
          </Box>
        </Box>
      </ScopeCard>

      <Box sx={{ display: "grid", gridTemplateRows: "repeat(3, minmax(0, 1fr))", gap: 2 }}>
        <ScopeCard
          title="merge_safe"
          subtitle="Deterministic validation subset"
          active={launcherScope === "merge_safe"}
          onClick={() => onScopeChange?.("merge_safe")}
        />
        <ScopeCard
          title={nightlyLabel}
          subtitle="Primary nightly validation tier"
          active={launcherScope === "nightly"}
          onClick={() => onScopeChange?.("nightly")}
        />
        <ScopeCard
          title="All cases"
          subtitle="Full available suite for the selected family"
          active={launcherScope === "all"}
          onClick={() => onScopeChange?.("all")}
        />
      </Box>
    </Box>
  );
}
