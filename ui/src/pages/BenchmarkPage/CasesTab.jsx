import React, { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";

import { listBenchmarkCases } from "../../services/benchmarkApi.js";
import { CursorButton } from "../../components/common/index.js";
import CaseDetailDialog from "./CaseDetailDialog.jsx";

function _normalizeTier(v) {
  if (!v || v === "all") return null;
  return v;
}

export default function CasesTab() {
  const [family, setFamily] = useState("layer1");
  const [tier, setTier] = useState("merge_safe");
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [casesPayload, setCasesPayload] = useState(null);

  const [selectedCaseId, setSelectedCaseId] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const tierResolved = useMemo(() => _normalizeTier(tier), [tier]);
  const items = casesPayload?.items || [];
  const total = casesPayload?.total || 0;

  async function loadCases() {
    setError(null);
    setLoading(true);
    try {
      const resp = await listBenchmarkCases({
        family,
        tier: tierResolved,
        q: q.trim() || null,
        limit: 200,
        offset: 0,
      });
      setCasesPayload(resp);
    } catch (e) {
      setError(e?.message || "failed_to_load_cases");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCases().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tier, family]);

  return (
    <Box sx={{ padding: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap", mb: 2 }}>
        <Typography sx={{ fontWeight: 600 }}>Cases</Typography>
        <Select
          size="small"
          value={family}
          onChange={(e) => {
            const f = e.target.value;
            setFamily(f);
            if (f === "layer1" && tier === "nightly_semantic") setTier("merge_safe");
            if (f === "graph" && tier === "nightly_semantic") setTier("merge_safe");
          }}
          sx={{ minWidth: 120 }}
        >
          <MenuItem value="layer1">layer1</MenuItem>
          <MenuItem value="layer2">layer2</MenuItem>
          <MenuItem value="graph">graph</MenuItem>
        </Select>
        <Select
          size="small"
          value={tier}
          onChange={(e) => setTier(e.target.value)}
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="all">all</MenuItem>
          <MenuItem value="merge_safe">merge_safe</MenuItem>
          <MenuItem value="nightly_heavy">nightly_heavy</MenuItem>
          {family === "layer2" ? <MenuItem value="nightly_semantic">nightly_semantic</MenuItem> : null}
        </Select>

        <TextField
          size="small"
          label="search case_id"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          sx={{ minWidth: 260 }}
        />

        <CursorButton onClick={() => loadCases()} disabled={loading}>
          {loading ? "loading..." : "Search"}
        </CursorButton>
      </Box>

      {error && (
        <Typography sx={{ color: "rgba(239, 68, 68, 0.9)", mb: 1 }} role="alert">
          {error}
        </Typography>
      )}

      <Typography sx={{ color: "rgba(255,255,255,0.6)", mb: 1 }}>
        Total: {total}
      </Typography>

      {items.length === 0 ? (
        <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>No cases found.</Typography>
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>case_id</TableCell>
              <TableCell>tier</TableCell>
              <TableCell>article</TableCell>
              <TableCell>{family === "layer2" ? "semantic_gold" : "gold.json"}</TableCell>
              {family === "layer2" || family === "graph" ? null : (
                <TableCell>graph_exp</TableCell>
              )}
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((c) => (
              <TableRow key={c.case_id}>
                <TableCell sx={{ wordBreak: "break-all" }}>{c.case_id}</TableCell>
                <TableCell>{c.tier || "-"}</TableCell>
                <TableCell>{c.has_article_md ? "yes" : "no"}</TableCell>
                <TableCell>{family === "layer2" ? (c.has_semantic_gold ? "yes" : "no") : c.has_gold_json ? "yes" : "no"}</TableCell>
                {family === "layer2" || family === "graph" ? null : (
                  <TableCell>{c.has_graph_expectations ? "yes" : "no"}</TableCell>
                )}
                <TableCell align="right">
                  <CursorButton
                    onClick={() => {
                      setSelectedCaseId(c.case_id);
                      setDialogOpen(true);
                    }}
                  >
                    Preview
                  </CursorButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <CaseDetailDialog
        open={dialogOpen}
        caseId={selectedCaseId}
        family={family}
        onClose={() => {
          setDialogOpen(false);
          setSelectedCaseId(null);
        }}
      />
    </Box>
  );
}


