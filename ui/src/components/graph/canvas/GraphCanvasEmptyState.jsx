import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { MIN_CANVAS_HEIGHT } from "./graphCanvasMvpConstants.js";

export default function GraphCanvasEmptyState({ tk, message }) {
  return (
    <Box
      sx={{
        borderRadius: "6px",
        border: `1px solid ${tk.border.default}`,
        backgroundColor: tk.surface.panel,
        minHeight: MIN_CANVAS_HEIGHT,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        p: 2,
      }}
    >
      <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted }}>{message}</Typography>
    </Box>
  );
}
