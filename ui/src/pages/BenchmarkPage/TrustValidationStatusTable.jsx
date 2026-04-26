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
 * @param {{ rows: Array<{ familyKey: string, memberId: string, aggregate: string }>, t: (key: string) => string }} props
 */
export default function TrustValidationStatusTable({ rows, t }) {
  if (!rows?.length) return null;
  return (
    <div>
      <Table size="small" padding="none" sx={{ borderCollapse: "separate" }}>
        <TableHead>
          <TableRow>
            <TableCell sx={{ ...cellSx, color: "rgba(255,255,255,0.55)", fontWeight: 600 }}>
              {t("benchmarkPage.trustDrillIn.colMember")}
            </TableCell>
            <TableCell sx={{ ...cellSx, color: "rgba(255,255,255,0.55)", fontWeight: 600 }}>
              {t("benchmarkPage.trustDrillIn.colValidationStatus")}
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((r) => (
            <TableRow key={`${r.familyKey}.${r.memberId}`}>
              <TableCell sx={{ ...cellSx, color: "rgba(255,255,255,0.82)", fontFamily: "monospace" }}>
                {r.familyKey}.{r.memberId}
              </TableCell>
              <TableCell sx={{ ...cellSx, color: "rgba(255,255,255,0.85)" }}>{r.aggregate}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
