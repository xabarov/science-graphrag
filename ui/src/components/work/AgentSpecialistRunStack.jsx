import React, { useState } from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import { CursorSmallButton } from "../common/index.js";
import { buildSpecialistStreamGroups, formatStreamEventOneLine } from "./agentRunViewModel.js";

/**
 * Compact per-specialist grouping of stream events (no new SSE types required).
 *
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   streamEvents: unknown[],
 * }} props
 */
export function AgentSpecialistRunStack({ t, streamEvents }) {
  const groups = buildSpecialistStreamGroups(streamEvents);
  if (groups.length === 0) return null;

  return (
    <Box sx={{ mb: 1 }}>
      <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.42)", mb: 0.5 }}>
        {t("chat.run.specialistRunsTitle")}
      </Typography>
      {groups.map((g) => (
        <SpecialistRunGroup key={g.key} t={t} group={g} />
      ))}
    </Box>
  );
}

/**
 * @param {{ t: Function, group: { key: string, from: string, to: string, isOrphan: boolean, events: unknown[] } }} props
 */
function SpecialistRunGroup({ t, group }) {
  const [open, setOpen] = useState(false);
  const n = group.events.length;
  const label = group.isOrphan
    ? t("chat.run.specialistOrphanLabel", { count: String(n) })
    : t("chat.run.specialistRunLabel", { from: group.from || "—", to: group.to || "—", count: String(n) });

  return (
    <Box sx={{ mb: 0.75, border: "1px solid rgba(255,255,255,0.06)", borderRadius: "6px", px: 1, py: 0.5 }}>
      <CursorSmallButton
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={open ? t("chat.run.specialistCollapseAria") : t("chat.run.specialistExpandAria")}
        sx={{ minHeight: 26, py: 0.25 }}
      >
        {open ? t("chat.run.specialistCollapse") : t("chat.run.specialistExpand")} {label}
      </CursorSmallButton>
      <Collapse in={open} timeout="auto" unmountOnExit>
        <Box sx={{ pl: 0.5, pt: 0.5 }}>
          {group.events.map((ev, idx) => {
            const line = formatStreamEventOneLine(t, ev);
            const type = ev && typeof ev === "object" ? String(ev.type || "") : "";
            const text = line || type || "—";
            return (
              <Typography
                key={`${group.key}-${idx}-${type}`}
                sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.45)", lineHeight: 1.35, mb: 0.15 }}
              >
                {text}
              </Typography>
            );
          })}
        </Box>
      </Collapse>
    </Box>
  );
}
