import React, { useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";

import AskPanel from "../components/work/AskPanel.jsx";
import PageHeader from "../components/layout/PageHeader.jsx";
import { CursorSmallButton } from "../components/common/index.js";
import { persistWorkId } from "./WorkspacePage/utils/workContext.js";

/** Standalone Ask entry; workspace tab is the primary UX when a work is selected. */
export default function AskPage() {
  const [searchParams] = useSearchParams();
  const initialWorkId = searchParams.get("work_id") || "";

  useEffect(() => {
    if (initialWorkId.trim()) persistWorkId(initialWorkId);
  }, [initialWorkId]);

  return (
    <Box sx={{ p: 2, maxWidth: 960 }}>
      <PageHeader
        eyebrow="Direct tool"
        title="Ask"
        description="Run a standalone question when you want a quick query surface. Use Workspace Ask when the answer should stay tied to the active reading context."
        actions={
          <>
            <CursorSmallButton component={Link} to="/workspace" sx={{ textDecoration: "none" }}>
              Workspace
            </CursorSmallButton>
            <CursorSmallButton component={Link} to="/corpus" sx={{ textDecoration: "none" }}>
              Corpus
            </CursorSmallButton>
          </>
        }
      />
      <AskPanel initialWorkId={initialWorkId} showPageChrome={false} />
    </Box>
  );
}
