import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";

import { CursorPrimaryButton, CursorSmallButton } from "../components/common/index.js";
import EvidenceWorkBody from "../components/work/EvidenceWorkBody.jsx";
import { buildWorkspacePath, persistWorkId } from "./WorkspacePage/utils/workContext.js";

export default function EvidencePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initial = searchParams.get("work_id") || "";
  const [workIdInput, setWorkIdInput] = useState(initial);

  const workId = searchParams.get("work_id") || "";

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
      <Typography sx={{ fontWeight: 600, mb: 1, color: "rgba(255,255,255,0.9)" }}>Evidence</Typography>
      <Typography sx={{ color: "rgba(255,255,255,0.6)", fontSize: "0.8125rem", mb: 2 }}>
        Direct entry: chunk fingerprints for traceability. Prefer <strong>Workspace → Evidence</strong> for the main flow.
      </Typography>

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

      {workId.trim() ? (
        <Box sx={{ mb: 1.5 }}>
          <CursorSmallButton component={Link} to={buildWorkspacePath(workId, "reader")} sx={{ textDecoration: "none" }}>
            Open Reader in workspace
          </CursorSmallButton>
        </Box>
      ) : null}

      {workId.trim() ? <EvidenceWorkBody workId={workId} /> : null}
    </Box>
  );
}
