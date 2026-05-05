import React from "react";
import Box from "@mui/material/Box";

/** @typedef {"subtle" | "normal" | "strong"} ShimmerIntensity */

/** @type {Record<ShimmerIntensity, { gradient: string, durationSec: number }>} */
const INTENSITY_PRESETS = {
  subtle: {
    gradient:
      "linear-gradient(90deg, rgba(160, 160, 170, 0.28) 0%, rgba(200, 200, 210, 0.55) 50%, rgba(160, 160, 170, 0.28) 100%)",
    durationSec: 3.2,
  },
  normal: {
    gradient:
      "linear-gradient(90deg, rgba(192, 192, 200, 0.40) 0%, rgba(220, 220, 230, 0.82) 50%, rgba(192, 192, 200, 0.40) 100%)",
    durationSec: 2.6,
  },
  strong: {
    gradient:
      "linear-gradient(90deg, rgba(200, 200, 215, 0.55) 0%, rgba(235, 235, 245, 0.95) 50%, rgba(200, 200, 215, 0.55) 100%)",
    durationSec: 2.1,
  },
};

/**
 * Single-line silver shimmer label for active agent states (reduced-motion safe).
 *
 * @param {{
 *   children: React.ReactNode,
 *   sx?: object,
 *   component?: React.ElementType,
 *   intensity?: ShimmerIntensity,
 * }} props
 */
export function ShimmerLabel({ children, sx = {}, component = "span", intensity = "normal", ...rest }) {
  const preset = INTENSITY_PRESETS[intensity] || INTENSITY_PRESETS.normal;
  const dur = `${preset.durationSec}s`;
  return (
    <Box
      component={component}
      {...rest}
      sx={{
        display: "inline-block",
        background: preset.gradient,
        backgroundSize: "200% 100%",
        backgroundClip: "text",
        WebkitBackgroundClip: "text",
        WebkitTextFillColor: "transparent",
        animation: `agentShimmer ${dur} ease-in-out infinite`,
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
