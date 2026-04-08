import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";

import { CursorPrimaryButton, CursorSmallButton } from "../components/common/index.js";
import PageHeader from "../components/layout/PageHeader.jsx";
import ReaderWorkBody from "../components/work/ReaderWorkBody.jsx";
import { persistWorkId } from "./WorkspacePage/utils/workContext.js";
import { buildWorkspaceTracePath, readTraceabilityState } from "../components/work/traceabilityState.js";

export default function ReaderPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initial = searchParams.get("work_id") || "";
  const [workIdInput, setWorkIdInput] = useState(initial);

  const workId = searchParams.get("work_id") || "";
  const trace = readTraceabilityState(searchParams);

  useEffect(() => {
    setWorkIdInput(workId);
  }, [workId]);

  useEffect(() => {
    if (workId.trim()) persistWorkId(workId);
  }, [workId]);

  function applyWorkId(e) {
    e.preventDefault();
    const next = workIdInput.trim();
    if (next) {
      persistWorkId(next);
      setSearchParams({ work_id: next });
    } else setSearchParams({});
  }

  return (
    <Box sx={{ p: 2, maxWidth: 960 }}>
      <PageHeader
        eyebrow="Direct tool"
        title="Reader"
        description={
          <>
            Load a specific <code style={{ color: "rgba(129,140,248,0.95)" }}>work_id</code> for focused reading. Prefer <strong>Workspace → Reader</strong>{" "}
            when you want to stay inside the full research flow.
          </>
        }
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

      <Box component="form" onSubmit={applyWorkId} sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
        <TextField
          label="work_id"
          value={workIdInput}
          onChange={(ev) => setWorkIdInput(ev.target.value)}
          size="small"
          fullWidth
          sx={{
            maxWidth: 480,
            "& .MuiInputBase-input": { fontSize: "0.8125rem" },
            "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
          }}
        />
        <CursorPrimaryButton type="submit">Load</CursorPrimaryButton>
      </Box>

      {!workId.trim() ? (
        <Box
          sx={{
            p: 2,
            borderRadius: "6px",
            border: "1px dashed rgba(255,255,255,0.12)",
            backgroundColor: "rgba(255,255,255,0.02)",
          }}
        >
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)" }}>No work loaded</Typography>
          <Typography sx={{ mt: 0.75, fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)" }}>
            Enter a `work_id` above or start from the corpus to open a paper in workspace-first mode.
          </Typography>
        </Box>
      ) : null}
      {workId.trim() ? (
        <ReaderWorkBody
          workId={workId}
          focusedFingerprint={trace.chunkFingerprint}
          focusedSection={trace.section}
          citation={trace.citation}
        />
      ) : null}
      {workId.trim() ? (
        <Box sx={{ mt: 1.5, display: "flex", flexWrap: "wrap", gap: 1 }}>
          <CursorSmallButton
            component={Link}
            to={buildWorkspaceTracePath(workId, "reader", {
              chunkFingerprint: trace.chunkFingerprint,
              section: trace.section,
              citation: trace.citation,
            })}
            sx={{ textDecoration: "none" }}
          >
            Open Reader in workspace
          </CursorSmallButton>
          <CursorSmallButton
            component={Link}
            to={buildWorkspaceTracePath(workId, "graph", {
              section: trace.section,
              citation: trace.citation,
            })}
            sx={{ textDecoration: "none" }}
          >
            Open Graph in workspace
          </CursorSmallButton>
        </Box>
      ) : null}
    </Box>
  );
}
