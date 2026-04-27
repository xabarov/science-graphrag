import React from "react";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import { useTheme } from "@mui/material/styles";

/**
 * @param {{ rows: Array<{ family: string, memberId: string, caseId: string, passed: boolean | null }>, t: (key: string) => string }} props
 */
export default function TrustAdvisoryFailuresTable({ rows, t }) {
  const tk = useTheme().appTokens;
  const cellSx = {
    borderColor: tk.border.default,
    fontSize: "0.75rem",
    py: 0.5,
    px: 1,
  };
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
          <TableCell sx={{ ...cellSx, color: tk.text.muted, fontWeight: 600 }}>
            {t("benchmarkPage.trustDrillIn.colCaseId")}
          </TableCell>
          <TableCell sx={{ ...cellSx, color: tk.text.muted, fontWeight: 600 }}>
            {t("benchmarkPage.trustDrillIn.colSource")}
          </TableCell>
          <TableCell sx={{ ...cellSx, color: tk.text.muted, fontWeight: 600 }}>
            {t("benchmarkPage.trustDrillIn.colPassed")}
          </TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map((r, i) => (
          <TableRow key={`${r.caseId}-${r.family}.${r.memberId}-${i}`}>
            <TableCell sx={{ ...cellSx, color: tk.text.primary, fontFamily: "monospace" }}>
              {r.caseId || "—"}
            </TableCell>
            <TableCell sx={{ ...cellSx, color: tk.text.primary, fontFamily: "monospace" }}>
              {r.family && r.memberId ? `${r.family}.${r.memberId}` : "—"}
            </TableCell>
            <TableCell sx={{ ...cellSx, color: tk.text.secondary }}>{passedLabel(r.passed)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
