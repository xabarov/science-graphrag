import React from "react";
import { useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";

import AskPanel from "../components/work/AskPanel.jsx";

/** Standalone Ask entry; workspace tab is the primary UX when a work is selected. */
export default function AskPage() {
  const [searchParams] = useSearchParams();
  const initialWorkId = searchParams.get("work_id") || "";

  return (
    <Box sx={{ p: 2, maxWidth: 960 }}>
      <AskPanel initialWorkId={initialWorkId} showPageChrome />
    </Box>
  );
}
