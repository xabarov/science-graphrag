import React, { useMemo } from "react";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import LinearProgress from "@mui/material/LinearProgress";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

const STATUS_ORDER = { in_progress: 0, pending: 1, completed: 2, cancelled: 3 };

/**
 * Structured plan from ``session_meta.research_plan`` (mirrored in ``run_metadata.research_plan``).
 *
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   plan: { items?: Array<{ id: string, content: string, status: string }>, ui_mode?: string } | null | undefined,
 *   streamHint: { item_count?: number, updated_at?: number } | null,
 * }} props
 */
export default function AskResearchPlanPanel({ t, plan, streamHint }) {
  const tk = useTheme().appTokens;

  const { items, isOutline } = useMemo(() => {
    const raw = plan && Array.isArray(plan.items) ? plan.items : [];
    const mapped = raw
      .filter((x) => x && typeof x === "object" && String(x.id || "").trim())
      .map((x) => ({
        id: String(x.id),
        content: String(x.content || "").trim(),
        status: String(x.status || "pending").toLowerCase(),
      }));
    const uiMode = String(plan?.ui_mode || "").toLowerCase().trim();
    if (uiMode === "checklist") {
      const sorted = [...mapped].sort((a, b) => {
        const oa = STATUS_ORDER[a.status] ?? 9;
        const ob = STATUS_ORDER[b.status] ?? 9;
        if (oa !== ob) return oa - ob;
        return a.id.localeCompare(b.id);
      });
      return { items: sorted, isOutline: false };
    }
    if (uiMode === "outline") {
      return { items: mapped, isOutline: true };
    }
    /* Legacy plans without ui_mode: treat as checklist if statuses look like a tracker. */
    const looksLikeChecklist = mapped.some(
      (x) => x.status !== "pending" && x.status !== "cancelled",
    );
    if (looksLikeChecklist) {
      const sorted = [...mapped].sort((a, b) => {
        const oa = STATUS_ORDER[a.status] ?? 9;
        const ob = STATUS_ORDER[b.status] ?? 9;
        if (oa !== ob) return oa - ob;
        return a.id.localeCompare(b.id);
      });
      return { items: sorted, isOutline: false };
    }
    return { items: mapped, isOutline: true };
  }, [plan]);

  const title = t("askPanel.researchPlan.title");
  const empty = t("askPanel.researchPlan.empty");
  const hintCount =
    streamHint && Number.isFinite(Number(streamHint.item_count)) ? Number(streamHint.item_count) : null;

  return (
    <Box
      sx={{
        width: { xs: "100%", md: 240 },
        flexShrink: 0,
        minHeight: 0,
        maxHeight: { xs: "min(36vh, 320px)", md: "none" },
        height: { md: "100%" },
        display: "flex",
        flexDirection: "column",
        borderRadius: "6px",
        border: `1px solid ${tk.border.default}`,
        backgroundColor: tk.surface.panelAlt,
        overflow: "hidden",
      }}
    >
      <Box sx={{ px: 1.1, py: 1, borderBottom: `1px solid ${tk.border.default}`, flexShrink: 0 }}>
        <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: tk.text.primary }}>{title}</Typography>
        {hintCount != null && items.length === 0 ? (
          <Typography sx={{ fontSize: "0.7rem", color: tk.text.muted, mt: 0.5 }}>
            {t("askPanel.researchPlan.updating", { count: String(hintCount) })}
          </Typography>
        ) : null}
      </Box>
      <Box sx={{ flex: 1, overflowY: "auto", py: 0.75, px: 1 }}>
        {items.length === 0 ? (
          <Typography sx={{ fontSize: "0.75rem", color: tk.text.faint, lineHeight: 1.45 }}>{empty}</Typography>
        ) : isOutline ? (
          <Box component="ol" sx={{ m: 0, pl: 2.1, color: tk.text.primary }}>
            {items.map((row) => (
              <Box
                component="li"
                key={row.id}
                sx={{
                  py: 0.45,
                  borderBottom: `1px solid ${tk.border.subtle}`,
                  "&:last-of-type": { borderBottom: "none" },
                  fontSize: "0.75rem",
                  lineHeight: 1.35,
                }}
              >
                <Typography sx={{ fontSize: "0.75rem", color: tk.text.primary, lineHeight: 1.35 }}>
                  {row.content}
                </Typography>
              </Box>
            ))}
          </Box>
        ) : (
          items.map((row) => (
            <Box
              key={row.id}
              sx={{
                display: "flex",
                alignItems: "flex-start",
                gap: 0.75,
                py: 0.5,
                borderBottom: `1px solid ${tk.border.subtle}`,
                "&:last-of-type": { borderBottom: "none" },
              }}
            >
              <Checkbox
                size="small"
                checked={row.status === "completed"}
                indeterminate={row.status === "in_progress"}
                disabled
                sx={{ p: 0, mt: -0.25 }}
                inputProps={{ "aria-label": row.content }}
              />
              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Typography
                  sx={{
                    fontSize: "0.75rem",
                    color: row.status === "cancelled" ? tk.text.faint : tk.text.primary,
                    textDecoration: row.status === "completed" ? "line-through" : "none",
                    lineHeight: 1.35,
                  }}
                >
                  {row.content}
                </Typography>
                <Typography sx={{ fontSize: "0.65rem", color: tk.text.muted, mt: 0.25 }}>
                  {row.status}
                </Typography>
              </Box>
            </Box>
          ))
        )}
      </Box>
      {hintCount != null && items.length === 0 ? (
        <Box sx={{ px: 1, pb: 1 }}>
          <LinearProgress variant="indeterminate" sx={{ height: 2, borderRadius: 1 }} />
        </Box>
      ) : null}
    </Box>
  );
}
