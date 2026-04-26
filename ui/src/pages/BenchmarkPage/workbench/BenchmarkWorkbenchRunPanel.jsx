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

import MetricsCard from "../../../components/MetricsCard.jsx";
import { getBenchmarkRunCasesPage } from "../../../services/benchmarkApi.js";
import { CursorButton } from "../../../components/common/index.js";
import {
  collectFailedCheckNames,
  filterCasesByFailure,
  sortBenchmarkCases,
  sortOptionsForFamily,
} from "../benchmarkRunUiHelpers.js";
import { useI18n } from "../../../i18n/I18nContext.jsx";

function Panel({ title, children }) {
  return (
    <Box
      sx={{
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: 1.5,
        backgroundColor: "#1a1a1a",
        padding: 1.5,
        minHeight: 220,
      }}
    >
      <Typography sx={{ fontWeight: 600, mb: 1 }}>{title}</Typography>
      {children}
    </Box>
  );
}

function JsonBlock({ value }) {
  return (
    <Box
      component="pre"
      sx={{
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
        maxHeight: 360,
        overflow: "auto",
        margin: 0,
        fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
        fontSize: "12px",
        color: "rgba(255,255,255,0.85)",
      }}
    >
      {JSON.stringify(value, null, 2)}
    </Box>
  );
}

function formatComparisonCellValue(value, fallback = null) {
  const resolved = value !== undefined ? value : fallback;
  return JSON.stringify(resolved);
}

const CASES_PAGE_SIZE = 500;

/** Filters + case list reset via `key={runId}` on the parent. */
export function WorkbenchRunScopedPanel({ runDetail, caseDetail, selectedCaseId, onSelectCase }) {
  const { t } = useI18n();
  const runId = runDetail?.run_id;
  const casesTotal = runDetail?.cases_total ?? 0;
  const [loadedCases, setLoadedCases] = useState(() => runDetail?.cases ?? []);
  const [casesLoading, setCasesLoading] = useState(false);
  const [casesPageError, setCasesPageError] = useState(null);

  useEffect(() => {
    setLoadedCases(runDetail?.cases ?? []);
    setCasesPageError(null);
  }, [runId, runDetail?.cases]);

  const hasMoreCases =
    runDetail?.cases_paginated === true && loadedCases.length < (casesTotal || loadedCases.length);

  async function handleLoadMoreCases() {
    if (!runId || casesLoading) return;
    setCasesLoading(true);
    setCasesPageError(null);
    try {
      const resp = await getBenchmarkRunCasesPage(runId, {
        offset: loadedCases.length,
        limit: CASES_PAGE_SIZE,
      });
      const pg = resp?.data || resp;
      const items = pg.items || [];
      setLoadedCases((prev) => [...prev, ...items]);
    } catch (e) {
      setCasesPageError(e?.message || "failed_to_load_cases");
    } finally {
      setCasesLoading(false);
    }
  }

  const rawCases = loadedCases;
  const family = runDetail?.benchmark_family || "layer1";
  const [sortKey, setSortKey] = useState("case_id");
  const [sortDir, setSortDir] = useState("asc");
  const [failureMode, setFailureMode] = useState("all");
  const [selectedChecks, setSelectedChecks] = useState([]);

  const checkNames = useMemo(() => collectFailedCheckNames(rawCases), [rawCases]);
  const caseRows = useMemo(() => {
    const filtered = filterCasesByFailure(rawCases, failureMode, selectedChecks);
    return sortBenchmarkCases(filtered, sortKey, sortDir);
  }, [failureMode, rawCases, selectedChecks, sortKey, sortDir]);
  const sortOptions = sortOptionsForFamily(family);

  const comparisonRows =
    caseDetail?.comparison?.metadata_rows ||
    caseDetail?.comparison?.method_rows ||
    [];

  return (
    <>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap", mb: 2 }}>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel id="wb-sort-key">{t("benchmark.workbench.sort")}</InputLabel>
          <Select
            labelId="wb-sort-key"
            label={t("benchmark.workbench.sort")}
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value)}
          >
            {sortOptions.map((opt) => (
              <MenuItem key={opt.key} value={opt.key}>
                {t(`benchmark.sortOption.${opt.key}`)}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 100 }}>
          <InputLabel id="wb-sort-dir">{t("benchmark.workbench.dir")}</InputLabel>
          <Select
            labelId="wb-sort-dir"
            label={t("benchmark.workbench.dir")}
            value={sortDir}
            onChange={(e) => setSortDir(e.target.value)}
          >
            <MenuItem value="asc">{t("benchmark.workbench.asc")}</MenuItem>
            <MenuItem value="desc">{t("benchmark.workbench.desc")}</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel id="wb-fail">{t("benchmark.workbench.failures")}</InputLabel>
          <Select
            labelId="wb-fail"
            label={t("benchmark.workbench.failures")}
            value={failureMode}
            onChange={(e) => {
              setFailureMode(e.target.value);
              if (e.target.value !== "checks") setSelectedChecks([]);
            }}
          >
            <MenuItem value="all">{t("benchmark.workbench.allCases")}</MenuItem>
            <MenuItem value="any">{t("benchmark.workbench.anyFailed")}</MenuItem>
            <MenuItem value="checks" disabled={!checkNames.length}>
              {t("benchmark.workbench.byCheck")}
            </MenuItem>
          </Select>
        </FormControl>
        {failureMode === "checks" && checkNames.length ? (
          <FormControl size="small" sx={{ minWidth: 220 }}>
            <InputLabel id="wb-checks">{t("benchmark.workbench.checks")}</InputLabel>
            <Select
              labelId="wb-checks"
              label={t("benchmark.workbench.checks")}
              multiple
              value={selectedChecks}
              onChange={(e) => setSelectedChecks(e.target.value)}
              renderValue={(selected) => (selected.length ? selected.join(", ") : t("benchmark.workbench.checksPlaceholder"))}
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

      <Box sx={{ display: "grid", gridTemplateColumns: "280px minmax(0, 1fr) minmax(0, 1fr)", gap: 2 }}>
        <Panel title={t("benchmark.workbench.panelCases")}>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
            {caseRows.map((item) => (
              <Box
                key={item.case_id}
                role="button"
                tabIndex={0}
                onClick={() => onSelectCase?.(item.case_id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") onSelectCase?.(item.case_id);
                }}
                sx={{
                  padding: 1,
                  borderRadius: 1,
                  cursor: "pointer",
                  border: "1px solid rgba(255,255,255,0.08)",
                  backgroundColor:
                    selectedCaseId === item.case_id ? "rgba(99, 102, 241, 0.15)" : "transparent",
                  "&:hover": { backgroundColor: "rgba(255,255,255,0.04)" },
                }}
              >
                <Typography sx={{ fontSize: "0.8125rem", fontWeight: 500 }}>{item.case_id}</Typography>
                <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.6)" }}>
                  {item.status}
                  {item?.summary?.failed_checks?.length
                    ? ` | ${item.summary.failed_checks.join(", ")}`
                    : ""}
                </Typography>
              </Box>
            ))}
            {hasMoreCases ? (
              <Box sx={{ pt: 1 }}>
                <CursorButton onClick={handleLoadMoreCases} disabled={casesLoading}>
                  {casesLoading
                    ? t("benchmark.workbench.loadingCases")
                    : t("benchmark.workbench.loadMoreTpl", {
                        loaded: String(loadedCases.length),
                        total: String(casesTotal),
                      })}
                </CursorButton>
              </Box>
            ) : null}
            {casesPageError ? (
              <Typography sx={{ color: "rgba(239,68,68,0.9)", fontSize: "0.75rem", pt: 0.5 }} role="alert">
                {casesPageError}
              </Typography>
            ) : null}
          </Box>
        </Panel>

        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Panel title={t("benchmark.workbench.sourceArticle")}>
            {caseDetail ? (
              <>
                <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.6)", mb: 1 }}>
                  {t("benchmark.workbench.sections")}{" "}
                  {(caseDetail.article?.sections || []).map((item) => item.label).join(", ") || t("workspace.upload.dash")}
                </Typography>
                <Box
                  component="pre"
                  sx={{
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    maxHeight: 420,
                    overflow: "auto",
                    margin: 0,
                    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                    fontSize: "12px",
                  }}
                >
                  {caseDetail.article?.raw_markdown || ""}
                </Box>
              </>
            ) : (
              <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>{t("benchmark.workbench.selectCase")}</Typography>
            )}
          </Panel>

          <Panel title={t("benchmark.workbench.goldPayload")}>
            {caseDetail ? <JsonBlock value={caseDetail.gold?.payload || {}} /> : null}
          </Panel>
        </Box>

        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Panel title={t("benchmark.workbench.metrics")}>
            {caseDetail ? <MetricsCard metrics={caseDetail.metrics || {}} /> : null}
          </Panel>

          <Panel title={t("benchmark.workbench.prediction")}>
            {caseDetail ? <JsonBlock value={caseDetail.predicted?.payload || {}} /> : null}
          </Panel>

          <Panel title={t("benchmark.workbench.diff")}>
            {comparisonRows.length ? (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{t("benchmark.workbench.diffColField")}</TableCell>
                    <TableCell>{t("benchmark.workbench.diffColGold")}</TableCell>
                    <TableCell>{t("benchmark.workbench.diffColPred")}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {comparisonRows.map((row, idx) => (
                    <TableRow key={`${row.field || row.value || "row"}-${idx}`}>
                      <TableCell>{row.field || row.value || "-"}</TableCell>
                      <TableCell sx={{ maxWidth: 180, wordBreak: "break-word" }}>
                        {formatComparisonCellValue(row.gold_value, row.source)}
                      </TableCell>
                      <TableCell sx={{ maxWidth: 180, wordBreak: "break-word" }}>
                        {formatComparisonCellValue(row.predicted_value, row.status ?? "-")}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>{t("benchmark.workbench.noDiff")}</Typography>
            )}
          </Panel>
        </Box>
      </Box>
    </>
  );
}
