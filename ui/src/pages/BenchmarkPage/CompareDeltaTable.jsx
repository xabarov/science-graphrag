import React from "react";
import Box from "@mui/material/Box";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorSmallButton } from "../../components/common/index.js";
import { BENCHMARK_COMPARE_TABLE_CAP } from "./benchmarkCompareModel.js";

export default function CompareDeltaTable({ title, rows, onOpenCase, currentRunId, baselineRunId = null }) {
  const tk = useTheme().appTokens;
  if (!rows?.length) {
    return (
      <Box sx={{ mb: 2 }}>
        <Typography sx={{ fontWeight: 600, mb: 0.5 }}>{title}</Typography>
        <Typography sx={{ color: tk.text.muted, fontSize: "0.8125rem" }}>None</Typography>
      </Box>
    );
  }
  return (
    <Box sx={{ mb: 2 }}>
      <Typography sx={{ fontWeight: 600, mb: 1 }}>{title}</Typography>
      <Box sx={{ border: `1px solid ${tk.border.default}`, borderRadius: 1.5, overflow: "hidden" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>case_id</TableCell>
              <TableCell>metric</TableCell>
              <TableCell>baseline</TableCell>
              <TableCell>current</TableCell>
              <TableCell align="right">actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.slice(0, BENCHMARK_COMPARE_TABLE_CAP).map((row, idx) => (
              <TableRow key={`${row.case_id}-${row.metric}-${idx}`}>
                <TableCell sx={{ wordBreak: "break-word" }}>{row.case_id}</TableCell>
                <TableCell sx={{ fontSize: "0.75rem", color: tk.text.secondary }}>{row.metric}</TableCell>
                <TableCell>{String(row.baseline)}</TableCell>
                <TableCell>
                  {String(row.current)}
                  {row.delta != null ? ` (Δ ${Number(row.delta).toFixed(4)})` : ""}
                </TableCell>
                <TableCell align="right">
                  {onOpenCase && currentRunId ? (
                    <CursorSmallButton
                      onClick={() =>
                        onOpenCase(currentRunId, row.case_id, {
                          baselineRunId: baselineRunId || undefined,
                          metric: row.metric,
                        })
                      }
                    >
                      Workbench
                    </CursorSmallButton>
                  ) : null}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
      {rows.length > BENCHMARK_COMPARE_TABLE_CAP ? (
        <Typography sx={{ color: tk.text.muted, fontSize: "0.75rem", mt: 0.5 }}>
          Showing first {BENCHMARK_COMPARE_TABLE_CAP} of {rows.length}
        </Typography>
      ) : null}
    </Box>
  );
}
