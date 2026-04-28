import React from "react";
import SvgIcon from "@mui/material/SvgIcon";

/**
 * Renders a Simple Icons brand glyph in theme `currentColor`.
 *
 * @param {{ icon: import("simple-icons").SimpleIcon; sx?: import("@mui/system").SxProps }} props
 */
export default function BrandSvgIcon({ icon, sx }) {
  return (
    <SvgIcon inheritViewBox viewBox="0 0 24 24" titleAccess={icon.title} sx={{ fontSize: 22, flexShrink: 0, ...sx }}>
      <path d={icon.path} fill="currentColor" />
    </SvgIcon>
  );
}
