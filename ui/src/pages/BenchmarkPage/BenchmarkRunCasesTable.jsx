import React, { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { getBenchmarkRunCasesPage } from "../../services/benchmarkApi.js";
import { CursorButton, CursorSmallButton } from "../../components/common/index.js";
import {
  collectFailedCheckNames,
  filterCasesByFailure,
  sortBenchmarkCases,
  sortOptionsForFamily,
} from "./benchmarkRunUiHelpers.js";

const PAGE_SIZE = 100;

export default function BenchmarkRunCasesTable({ run, onOpenWorkbench }) {
  const tk = useTheme().appTokens;
  const rid = run?.run_id;
  const isPaginated = run?.cases_paginated === true;
  const totalFromRun = run?.cases_total ?? 0;

  const [fetchedRows, setFetchedRows] = useState([]);
  const [nextOffset, setNextOffset] = useState(0);
  const [pageLoading, setPageLoading] = useState(false);
  const [pageError, setPageError] = useState(null);

  const cases = useMemo(() => {
    if (isPaginated) return fetchedRows;
    return run?.cases ?? [];
  }, [isPaginated, fetchedRows, run]);

  async function fetchCasesPage(offset, append) {
    if (!rid) return;
    setPageLoading(true);
    setPageError(null);
    try {
      const resp = await getBenchmarkRunCasesPage(rid, { offset, limit: PAGE_SIZE });
      const data = resp?.data || resp;
      const items = data?.items || [];
      if (append) {
        setFetchedRows((prev) => [...prev, ...items]);
      } else {
        setFetchedRows(items);
      }
      setNextOffset(offset + items.length);
    } catch (e) {
      setPageError(e?.message || "failed_to_load_cases");
    } finally {
      setPageLoading(false);
    }
  }

  useEffect(() => {
    if (!isPaginated || !rid) {
      setFetchedRows([]);
      setNextOffset(0);
      setPageError(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setPageLoading(true);
      setPageError(null);
      try {
        const resp = await getBenchmarkRunCasesPage(rid, { offset: 0, limit: PAGE_SIZE });
        const data = resp?.data || resp;
        const items = data?.items || [];
        if (!cancelled) {
          setFetchedRows(items);
          setNextOffset(items.length);
        }
      } catch (e) {
        if (!cancelled) setPageError(e?.message || "failed_to_load_cases");
      } finally {
        if (!cancelled) setPageLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isPaginated, rid, run?.cases_paginated]);

  const family = run?.benchmark_family || "layer1";

  const [sortKey, setSortKey] = useState("case_id");
  const [sortDir, setSortDir] = useState("asc");
  const [failureMode, setFailureMode] = useState("all");
  const [selectedChecks, setSelectedChecks] = useState([]);

  const checkNames = useMemo(() => collectFailedCheckNames(cases), [cases]);

  const displayCases = useMemo(() => {
    const filtered = filterCasesByFailure(cases, failureMode, selectedChecks);
    return sortBenchmarkCases(filtered, sortKey, sortDir);
  }, [cases, failureMode, selectedChecks, sortKey, sortDir]);

  const sortOptions = sortOptionsForFamily(family);
  const hasMore = isPaginated && nextOffset < totalFromRun;

  if (!cases.length && isPaginated && pageLoading) {
    return <Typography sx={{ color: tk.text.secondary }}>Loading cases…</Typography>;
  }

  if (!cases.length) {
    return <Typography sx={{ color: tk.text.secondary }}>No cases in this run.</Typography>;
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
      {isPaginated ? (
        <Typography sx={{ color: tk.text.muted, fontSize: "0.8125rem" }}>
          Large run: showing {cases.length} of {totalFromRun} cases (paginated). Filters apply to loaded rows only.
        </Typography>
      ) : null}
      {pageError ? (
        <Typography sx={{ color: tk.state.dangerFg, fontSize: "0.8125rem" }} role="alert">
          {pageError}
        </Typography>
      ) : null}

      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel id="bench-sort-key">Sort by</InputLabel>
          <Select
            labelId="bench-sort-key"
            label="Sort by"
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value)}
          >
            {sortOptions.map((opt) => (
              <MenuItem key={opt.key} value={opt.key}>
                {opt.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel id="bench-sort-dir">Dir</InputLabel>
          <Select
            labelId="bench-sort-dir"
            label="Dir"
            value={sortDir}
            onChange={(e) => setSortDir(e.target.value)}
          >
            <MenuItem value="asc">asc</MenuItem>
            <MenuItem value="desc">desc</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 220 }}>
          <InputLabel id="bench-fail-filter">Failed checks</InputLabel>
          <Select
            labelId="bench-fail-filter"
            label="Failed checks"
            value={failureMode}
            onChange={(e) => {
              setFailureMode(e.target.value);
              if (e.target.value !== "checks") setSelectedChecks([]);
            }}
          >
            <MenuItem value="all">All cases</MenuItem>
            <MenuItem value="any">Any failed check</MenuItem>
            <MenuItem value="checks" disabled={!checkNames.length}>
              By check name…
            </MenuItem>
          </Select>
        </FormControl>
        {failureMode === "checks" && checkNames.length ? (
          <FormControl size="small" sx={{ minWidth: 260 }}>
            <InputLabel id="bench-check-pick">Checks</InputLabel>
            <Select
              labelId="bench-check-pick"
              label="Checks"
              multiple
              value={selectedChecks}
              onChange={(e) => setSelectedChecks(e.target.value)}
              renderValue={(selected) => (selected.length ? selected.join(", ") : "Select…")}
            >
              {checkNames.map((name) => (
                <MenuItem key={name} value={name}>
                  {name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        ) : null}
      </Box>

      <Box sx={{ border: `1px solid ${tk.border.default}`, borderRadius: 1.5, overflow: "hidden" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>case</TableCell>
              <TableCell>status</TableCell>
              <TableCell>summary</TableCell>
              <TableCell>failed checks</TableCell>
              <TableCell align="right">actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {displayCases.map((item) => {
              const failedChecks = item?.summary?.failed_checks || [];
              const summaryText =
                family === "layer2"
                  ? `p_methods ${(item?.summary?.precision_methods ?? 0).toFixed(2)} | L2 recall ${(item?.summary?.layer2_recall_ratio ?? 0).toFixed(3)}`
                  : `names ${(item?.summary?.names_f1 ?? 0).toFixed(2)} | arxiv ${(item?.summary?.sample_arxiv_f1 ?? 0).toFixed(2)}`;
              return (
                <TableRow key={item.case_id} hover>
                  <TableCell sx={{ wordBreak: "break-word" }}>{item.case_id}</TableCell>
                  <TableCell>{item.status}</TableCell>
                  <TableCell>{summaryText}</TableCell>
                  <TableCell sx={{ maxWidth: 280, color: tk.text.secondary }}>
                    {failedChecks.length ? failedChecks.join(", ") : "—"}
                  </TableCell>
                  <TableCell align="right">
                    <CursorSmallButton onClick={() => onOpenWorkbench?.(rid, item.case_id)}>
                      Open workbench
                    </CursorSmallButton>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </Box>

      {hasMore ? (
        <Box>
          <CursorButton onClick={() => fetchCasesPage(nextOffset, true)} disabled={pageLoading}>
            {pageLoading ? "Loading…" : "Load more cases"}
          </CursorButton>
        </Box>
      ) : null}
    </Box>
  );
}
