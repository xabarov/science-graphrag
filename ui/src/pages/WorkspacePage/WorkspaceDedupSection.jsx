import React from "react";
import Box from "@mui/material/Box";

import DeduplicationPanel from "../../components/graph/DeduplicationPanel.jsx";

/**
 * @param {{ workspaceId: string, onMerged: () => void }} props
 */
export default function WorkspaceDedupSection({ workspaceId, onMerged }) {
  if (!workspaceId) return null;
  return (
    <Box sx={{ mt: 2.5 }}>
      <DeduplicationPanel workspaceId={workspaceId} onMerged={onMerged} />
    </Box>
  );
}
