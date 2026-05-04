import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

export default function ChatUserBubble({ text }) {
  const tk = useTheme().appTokens;
  return (
    <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1.5 }}>
      <Box
        sx={{
          maxWidth: "min(720px, 92%)",
          px: 1.25,
          py: 1,
          borderRadius: "6px",
          backgroundColor: tk.accent.chipReadyBg,
          border: `1px solid ${tk.accent.softBorder}`,
        }}
      >
        <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, whiteSpace: "pre-wrap" }}>{text}</Typography>
      </Box>
    </Box>
  );
}
