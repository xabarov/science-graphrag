import React from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";

export default function SettingsSectionNav({ sections, activeSectionId, onSelect }) {
  return (
    <Box
      sx={{
        width: 250,
        borderRight: "1px solid rgba(255,255,255,0.08)",
        padding: 2,
        display: "flex",
        flexDirection: "column",
        gap: 1,
      }}
    >
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", letterSpacing: "0.04em" }}>
        Settings
      </Typography>
      {sections.map((section) => {
        const active = section.id === activeSectionId;
        const ready = section.status === "ready";
        return (
          <Box
            key={section.id}
            onClick={() => onSelect(section.id)}
            sx={{
              cursor: "pointer",
              borderRadius: 1.5,
              border: "1px solid rgba(255,255,255,0.08)",
              backgroundColor: active ? "rgba(99, 102, 241, 0.12)" : "#141414",
              padding: 1.25,
              transition: "all 0.15s ease",
              "&:hover": {
                borderColor: "rgba(255,255,255,0.16)",
                backgroundColor: active ? "rgba(99, 102, 241, 0.16)" : "rgba(255,255,255,0.04)",
              },
            }}
          >
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1 }}>
              <Typography sx={{ fontSize: "0.8125rem", fontWeight: 600 }}>{section.label}</Typography>
              <Chip
                label={ready ? "Ready" : "Soon"}
                size="small"
                sx={{
                  height: 20,
                  fontSize: "0.6875rem",
                  backgroundColor: ready ? "rgba(99, 102, 241, 0.12)" : "rgba(255,255,255,0.06)",
                  color: ready ? "rgba(129, 140, 248, 0.95)" : "rgba(255,255,255,0.55)",
                  border: "1px solid rgba(255,255,255,0.08)",
                }}
              />
            </Box>
            <Typography sx={{ marginTop: 0.75, fontSize: "0.75rem", color: "rgba(255,255,255,0.58)", lineHeight: 1.45 }}>
              {section.description}
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
}
