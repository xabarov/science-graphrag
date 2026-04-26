import React from "react";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";

const cellSx = {
  borderColor: "rgba(255,255,255,0.08)",
  fontSize: "0.75rem",
  py: 0.5,
  px: 1,
};

/**
 * @param {{ rows: Array<{ family: string, memberId: string, caseId: string, passed: boolean | null }>, t: (key: string) => string }} props
 */
export default function TrustAdvisoryFailuresTable({ rows, t }) {
  if (!rows?.length) return null;

  function passedLabel(passed) {
    if (passed === true) return t("benchmarkPage.trustDrillIn.passedYes");
    if (passed === false) return t("benchmarkPage.trustDrillIn.passedNo");
    return "—";
  }

  return (
    <Table size="small" padding="none" sx={{ borderCollapse: "separate" }}>
      <TableHead>
        <TableRow>
          <TableCell sx={{ ...cellSx, color: "rgba(255,255,255,0.55)", fontWeight: 600 }}>
            {t("benchmarkPage.trustDrillIn.colCaseId")}
          </TableCell>
          <TableCell sx={{ ...cellSx, color: "rgba(255,255,255,0.55)", fontWeight: 600 }}>
            {t("benchmarkPage.trustDrillIn.colSource")}
          </TableCell>
          <TableCell sx={{ ...cellSx, color: "rgba(255,255,255,0.55)", fontWeight: 600 }}>
            {t("benchmarkPage.trustDrillIn.colPassed")}
          </TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map((r, i) => (
          <TableRow key={`${r.caseId}-${r.family}.${r.memberId}-${i}`}>
            <TableCell sx={{ ...cellSx, color: "rgba(255,255,255,0.82)", fontFamily: "monospace" }}>
              {r.caseId || "—"}
            </TableCell>
            <TableCell sx={{ ...cellSx, color: "rgba(255,255,255,0.82)", fontFamily: "monospace" }}>
              {r.family && r.memberId ? `${r.family}.${r.memberId}` : "—"}
            </TableCell>
            <TableCell sx={{ ...cellSx, color: "rgba(255,255,255,0.75)" }}>{passedLabel(r.passed)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
