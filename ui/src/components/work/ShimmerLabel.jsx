import React from "react";
import Box from "@mui/material/Box";

/**
 * Single-line silver shimmer label for active agent states (reduced-motion safe).
 *
 * @param {{ children: React.ReactNode, sx?: object, component?: React.ElementType }} props
 */
export function ShimmerLabel({ children, sx = {}, component = "span", ...rest }) {
  return (
    <Box
      component={component}
      {...rest}
      sx={{
        display: "inline-block",
        background:
          "linear-gradient(90deg, rgba(192, 192, 200, 0.40) 0%, rgba(220, 220, 230, 0.82) 50%, rgba(192, 192, 200, 0.40) 100%)",
        backgroundSize: "200% 100%",
        backgroundClip: "text",
        WebkitBackgroundClip: "text",
        WebkitTextFillColor: "transparent",
        animation: "agentShimmer 2.6s ease-in-out infinite",
        "@keyframes agentShimmer": {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "@media (prefers-reduced-motion: reduce)": {
          animation: "none",
          background: "none",
          WebkitTextFillColor: "rgba(210, 210, 220, 0.78)",
          color: "rgba(210, 210, 220, 0.78)",
        },
        ...sx,
      }}
    >
      {children}
    </Box>
  );
}
