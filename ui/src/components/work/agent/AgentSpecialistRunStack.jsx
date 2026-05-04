import React, { useState } from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorSmallButton } from "../../common/index.js";
import { buildSpecialistStreamGroups, formatStreamEventOneLine } from "./agentRunViewModel.js";

/**
 * Compact per-specialist grouping of stream events (no new SSE types required).
 *
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   streamEvents: unknown[],
 *   compact?: boolean,
 * }} props
 */
export function AgentSpecialistRunStack({ t, streamEvents, compact = false }) {
  const tk = useTheme().appTokens;
  const groups = buildSpecialistStreamGroups(streamEvents);
  const [compactOpen, setCompactOpen] = useState(false);

  if (groups.length === 0) return null;

  const totalEvents = groups.reduce((acc, g) => acc + g.events.length, 0);

  if (compact) {
    return (
      <Box sx={{ mb: 1 }}>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 0.75,
            flexWrap: "wrap",
            mb: compactOpen ? 0.5 : 0,
          }}
        >
          <Typography component="span" sx={{ fontSize: "0.72rem", color: tk.text.muted }}>
            {t("chat.run.specialistCompactSummary", { count: String(totalEvents) })}
          </Typography>
          <Typography component="span" sx={{ fontSize: "0.72rem", color: tk.text.faint }}>
            ·
          </Typography>
          <CursorSmallButton
            type="button"
            onClick={() => setCompactOpen((v) => !v)}
            aria-expanded={compactOpen}
            aria-label={compactOpen ? t("chat.run.specialistCollapseAria") : t("chat.run.specialistExpandAria")}
            sx={{ minHeight: 26, py: 0.15, px: 0.75, color: tk.text.muted }}
          >
            {compactOpen ? t("chat.run.specialistCollapse") : t("chat.run.specialistExpand")}
          </CursorSmallButton>
        </Box>
        <Collapse in={compactOpen} timeout="auto" unmountOnExit>
          <Box sx={{ pt: 0.35 }}>
            {groups.map((g, idx) => (
              <SpecialistRunGroup key={g.key} t={t} group={g} panelId={`specialist-run-panel-${idx}`} />
            ))}
          </Box>
        </Collapse>
      </Box>
    );
  }

  return (
    <Box sx={{ mb: 1 }}>
      <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, mb: 0.5 }}>
        {t("chat.run.specialistRunsTitle")}
      </Typography>
      {groups.map((g, idx) => (
        <SpecialistRunGroup key={g.key} t={t} group={g} panelId={`specialist-run-panel-${idx}`} />
      ))}
    </Box>
  );
}

/**
 * @param {{ t: Function, group: { key: string, from: string, to: string, isOrphan: boolean, events: unknown[] }, panelId: string }} props
 */
function SpecialistRunGroup({ t, group, panelId }) {
  const tk = useTheme().appTokens;
  const [open, setOpen] = useState(false);
  const n = group.events.length;
  const label = group.isOrphan
    ? t("chat.run.specialistOrphanLabel", { count: String(n) })
    : t("chat.run.specialistRunLabel", { from: group.from || "—", to: group.to || "—", count: String(n) });

  return (
    <Box
      sx={{
        mb: 0.5,
        border: `1px solid ${tk.border.default}`,
        borderRadius: "6px",
        px: 0.75,
        py: 0.35,
        backgroundColor: tk.surface.subtle,
      }}
    >
      <CursorSmallButton
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={panelId}
        aria-label={open ? t("chat.run.specialistCollapseAria") : t("chat.run.specialistExpandAria")}
        sx={{
          minHeight: 26,
          py: 0.2,
          width: "100%",
          maxWidth: "100%",
          justifyContent: "flex-start",
          color: tk.text.muted,
          borderColor: tk.border.default,
          "&:hover": {
            backgroundColor: tk.control.navItemHoverBg,
            borderColor: tk.border.default,
          },
          "& > .MuiTypography-root": {
            display: "block",
            maxWidth: "100%",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            textAlign: "left",
          },
        }}
      >
        {open ? t("chat.run.specialistCollapse") : t("chat.run.specialistExpand")} {label}
      </CursorSmallButton>
      <Collapse in={open} timeout="auto" unmountOnExit>
        <Box id={panelId} role="region" aria-label={t("chat.run.specialistRunsTitle")} sx={{ pl: 0.5, pt: 0.5 }}>
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
