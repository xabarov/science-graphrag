import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import AskPanel from "../../../components/work/AskPanel.jsx";

/**
 * @param {{ workId: string }} props
 */
export default function AskTab({ workId }) {
  if (!workId.trim()) {
    return (
      <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>
        Pick a work from Corpus to scope questions to that work.
      </Typography>
    );
  }

  return (
    <Box>
      <AskPanel scopedWorkId={workId} showPageChrome={false} workspaceWorkId={workId} />
    </Box>
  );
}
