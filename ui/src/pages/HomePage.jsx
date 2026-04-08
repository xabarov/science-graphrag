import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { CursorPrimaryButton, CursorSmallButton } from "../components/common/index.js";
import PageHeader from "../components/layout/PageHeader.jsx";
import { isAdminModeEnabled } from "../components/layout/adminVisibility.js";
import { getContinueWorkspaceTarget, getHomeStatus, getRecentWorks } from "./HomePage/homeState.js";

function SurfaceCard({ eyebrow, title, description, actions, accent = "default" }) {
  const accentStyles =
    accent === "primary"
      ? {
          border: "1px solid rgba(99,102,241,0.24)",
          backgroundColor: "rgba(99,102,241,0.08)",
        }
      : {
          border: "1px solid rgba(255,255,255,0.08)",
          backgroundColor: "#1a1a1a",
        };

  return (
    <Box
      sx={{
        borderRadius: "6px",
        p: 2,
        minHeight: 172,
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        ...accentStyles,
      }}
    >
      <Box>
        <Typography sx={{ fontSize: "0.75rem", color: accent === "primary" ? "rgba(129,140,248,0.95)" : "rgba(255,255,255,0.45)", mb: 1 }}>
          {eyebrow}
        </Typography>
        <Typography sx={{ fontWeight: 600, fontSize: "0.9375rem", color: "rgba(255,255,255,0.9)" }}>{title}</Typography>
        <Typography sx={{ mt: 1, fontSize: "0.8125rem", color: "rgba(255,255,255,0.62)", lineHeight: 1.55 }}>
          {description}
        </Typography>
      </Box>
      <Box sx={{ mt: 2, display: "flex", flexWrap: "wrap", gap: 1 }}>{actions}</Box>
    </Box>
  );
}

export default function HomePage() {
  const continueTarget = useMemo(() => getContinueWorkspaceTarget(), []);
  const recentWorks = useMemo(() => getRecentWorks().slice(0, 4), []);
  const status = useMemo(() => getHomeStatus(), []);
  const adminModeEnabled = useMemo(() => isAdminModeEnabled(), []);

  return (
    <Box sx={{ p: 2, maxWidth: 1100 }}>
      <PageHeader
        eyebrow="Research surface"
        title="Home"
        description="Start from your last workspace, browse the corpus, or jump into admin tools without losing the main research flow."
        actions={
          <>
            <CursorSmallButton component={Link} to="/corpus" sx={{ textDecoration: "none" }}>
              Corpus
            </CursorSmallButton>
            {adminModeEnabled ? (
              <CursorSmallButton component={Link} to="/admin" sx={{ textDecoration: "none" }}>
                Admin
              </CursorSmallButton>
            ) : null}
          </>
        }
      />

      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 1.5 }}>
        <SurfaceCard
          eyebrow="Research surface"
          title={continueTarget ? "Continue last workspace" : "Start in corpus"}
          description={
            continueTarget
              ? "Resume the most recent work context and continue reading, asking questions, or checking evidence."
              : "No active workspace yet. Open the corpus to select a paper and start a research session."
          }
          accent="primary"
          actions={
            <>
              {continueTarget ? (
                <CursorPrimaryButton component={Link} to={continueTarget.path} sx={{ textDecoration: "none" }}>
                  Continue workspace
                </CursorPrimaryButton>
              ) : (
                <CursorPrimaryButton component={Link} to="/corpus" sx={{ textDecoration: "none" }}>
                  Open corpus
                </CursorPrimaryButton>
              )}
              <CursorSmallButton component={Link} to="/workspace" sx={{ textDecoration: "none" }}>
                Workspace
              </CursorSmallButton>
            </>
          }
        />

        <SurfaceCard
          eyebrow="Corpus browser"
          title="Browse indexed works"
          description="Use the corpus as the main entry to search, filter, and open papers into the workspace-first flow."
          actions={
            <>
              <CursorPrimaryButton component={Link} to="/corpus" sx={{ textDecoration: "none" }}>
                Open corpus
              </CursorPrimaryButton>
              <CursorSmallButton component={Link} to="/reader" sx={{ textDecoration: "none" }}>
                Direct reader
              </CursorSmallButton>
            </>
          }
        />

        {adminModeEnabled ? (
          <SurfaceCard
            eyebrow="Operations surface"
            title="Admin tools"
            description="Benchmarks, settings, and diagnostics stay available from a dedicated entry, without dominating the core research journey."
            actions={
              <>
                <CursorPrimaryButton component={Link} to="/admin" sx={{ textDecoration: "none" }}>
                  Open admin
                </CursorPrimaryButton>
                <CursorSmallButton component={Link} to="/admin/benchmarks" sx={{ textDecoration: "none" }}>
                  Benchmarks
                </CursorSmallButton>
              </>
            }
          />
        ) : null}
      </Box>

      <Box sx={{ mt: 2.5, display: "grid", gridTemplateColumns: "minmax(0, 2fr) minmax(280px, 1fr)", gap: 1.5 }}>
        <Box
          sx={{
            borderRadius: "6px",
            border: "1px solid rgba(255,255,255,0.08)",
            backgroundColor: "#1a1a1a",
            p: 2,
          }}
        >
          <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: "rgba(255,255,255,0.9)", mb: 1.25 }}>Recent works</Typography>
          {recentWorks.length === 0 ? (
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>
              No recent works yet. Open the corpus and start a workspace session to build a continue flow.
            </Typography>
          ) : (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              {recentWorks.map((item) => (
                <Box
                  key={item.workId}
                  sx={{
                    display: "flex",
                    flexWrap: "wrap",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: 1,
                    borderBottom: "1px solid rgba(255,255,255,0.06)",
                    pb: 1,
                  }}
                >
                  <Box sx={{ minWidth: 0 }}>
                    <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)", fontWeight: 600 }}>
                      {item.title || item.workId}
                    </Typography>
                    <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.35 }}>
                      {item.year ? `${item.year} · ` : ""}
                      {item.workId}
                    </Typography>
                  </Box>
                  <CursorSmallButton component={Link} to={`/workspace?work_id=${encodeURIComponent(item.workId)}&tab=${encodeURIComponent(item.tab || "overview")}`} sx={{ textDecoration: "none" }}>
                    Open
                  </CursorSmallButton>
                </Box>
              ))}
            </Box>
          )}
        </Box>

        <Box
          sx={{
            borderRadius: "6px",
            border: "1px solid rgba(255,255,255,0.08)",
            backgroundColor: "#1a1a1a",
            p: 2,
          }}
        >
          <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: "rgba(255,255,255,0.9)", mb: 1.25 }}>Session readiness</Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)", lineHeight: 1.6 }}>
            Last workspace context: {status.hasLastWork ? "saved locally" : "not saved yet"}
          </Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)", lineHeight: 1.6 }}>
            Recent work history: {status.hasRecentWorks ? "available" : "empty"}
          </Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)", lineHeight: 1.6 }}>
            Continue flow: {status.hasLocalState ? "ready to resume" : "starts from corpus"}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}
