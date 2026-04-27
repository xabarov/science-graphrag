import React from "react";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import { useTheme } from "@mui/material/styles";

/**
 * @param {{ rows: Array<{ familyKey: string, memberId: string, aggregate: string }>, t: (key: string) => string }} props
 */
export default function TrustValidationStatusTable({ rows, t }) {
  const tk = useTheme().appTokens;
  const cellSx = {
    borderColor: tk.border.default,
    fontSize: "0.75rem",
    py: 0.5,
    px: 1,
  };
  if (!rows?.length) return null;
  return (
    <div>
      <Table size="small" padding="none" sx={{ borderCollapse: "separate" }}>
        <TableHead>
          <TableRow>
            <TableCell sx={{ ...cellSx, color: tk.text.muted, fontWeight: 600 }}>
              {t("benchmarkPage.trustDrillIn.colMember")}
            </TableCell>
            <TableCell sx={{ ...cellSx, color: tk.text.muted, fontWeight: 600 }}>
              {t("benchmarkPage.trustDrillIn.colValidationStatus")}
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((r) => (
            <TableRow key={`${r.familyKey}.${r.memberId}`}>
              <TableCell sx={{ ...cellSx, color: tk.text.primary, fontFamily: "monospace" }}>
                {r.familyKey}.{r.memberId}
              </TableCell>
              <TableCell sx={{ ...cellSx, color: tk.text.primary }}>{r.aggregate}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
