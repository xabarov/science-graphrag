import React, { useEffect, useMemo } from "react";
import { Link, useLocation } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import AdminPanelSettingsOutlinedIcon from "@mui/icons-material/AdminPanelSettingsOutlined";
import ArticleOutlinedIcon from "@mui/icons-material/ArticleOutlined";
import AssessmentOutlinedIcon from "@mui/icons-material/AssessmentOutlined";
import FolderOpenOutlinedIcon from "@mui/icons-material/FolderOpenOutlined";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";

import { CursorIconAction } from "../components/common/index.js";
import PageHeader from "../components/layout/PageHeader.jsx";
import { mainShellContentSx } from "../components/layout/mainShellContentSx.js";
import { isAdminModeEnabled } from "../components/layout/adminVisibility.js";
import { useI18n } from "../i18n/useI18n.js";
import { getHomeStatus } from "./HomePage/homeState.js";
import { useCorpusEntryState } from "./HomePage/useCorpusEntryState.js";

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
      <Box sx={{ mt: 2, display: "flex", flexWrap: "wrap", gap: 0.75 }}>{actions}</Box>
    </Box>
  );
}

export default function HomePage() {
  const { t } = useI18n();
  const location = useLocation();
  const { recentWorks, continueTarget, refreshCorpusEntryState } = useCorpusEntryState({ recentLimit: 4 });
  const status = useMemo(() => getHomeStatus(), []);
  const adminModeEnabled = useMemo(() => isAdminModeEnabled(), []);

  useEffect(() => {
    refreshCorpusEntryState();
  }, [location.pathname, refreshCorpusEntryState]);

  return (
    <Box sx={{ p: 2, ...mainShellContentSx }}>
      <PageHeader
        eyebrow={t("home.header.eyebrow")}
        title={t("home.header.title")}
        description={t("home.header.description")}
        actions={
          <>
            <CursorIconAction component={Link} to="/workspaces" title={t("home.header.workspaces")}>
              <FolderOpenOutlinedIcon sx={{ fontSize: "1.1rem" }} />
            </CursorIconAction>
            {adminModeEnabled ? (
              <CursorIconAction component={Link} to="/admin" title={t("home.header.admin")}>
                <AdminPanelSettingsOutlinedIcon sx={{ fontSize: "1.1rem" }} />
              </CursorIconAction>
            ) : null}
          </>
        }
      />

      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 1.5 }}>
        <SurfaceCard
          eyebrow={t("home.card.workspace.eyebrow")}
          title={continueTarget ? t("home.card.workspace.titleOpenLast") : t("home.card.workspace.titleDefault")}
          description={
            continueTarget ? t("home.card.workspace.descOpenLast") : t("home.card.workspace.descDefault")
          }
          accent="primary"
          actions={
            <>
              <CursorIconAction component={Link} to="/workspace" title={t("home.card.workspace.openWorkspace")}>
                <HubOutlinedIcon sx={{ fontSize: "1.1rem" }} />
              </CursorIconAction>
              {continueTarget ? (
                <CursorIconAction component={Link} to={continueTarget.path} title={t("home.card.workspace.lastPaper")}>
                  <ArticleOutlinedIcon sx={{ fontSize: "1.1rem" }} />
                </CursorIconAction>
              ) : null}
              <CursorIconAction component={Link} to="/workspaces" title={t("home.card.workspace.browse")}>
                <FolderOpenOutlinedIcon sx={{ fontSize: "1.1rem" }} />
              </CursorIconAction>
            </>
          }
        />

        <SurfaceCard
          eyebrow={t("home.card.collections.eyebrow")}
          title={t("home.card.collections.title")}
          description={t("home.card.collections.description")}
          actions={
            <>
              <CursorIconAction component={Link} to="/workspaces" title={t("home.card.collections.workspaces")}>
                <FolderOpenOutlinedIcon sx={{ fontSize: "1.1rem" }} />
              </CursorIconAction>
              <CursorIconAction component={Link} to="/reader" title={t("home.card.collections.reader")}>
                <MenuBookOutlinedIcon sx={{ fontSize: "1.1rem" }} />
              </CursorIconAction>
            </>
          }
        />

        {adminModeEnabled ? (
          <SurfaceCard
            eyebrow={t("home.card.admin.eyebrow")}
            title={t("home.card.admin.title")}
            description={t("home.card.admin.description")}
            actions={
              <>
                <CursorIconAction component={Link} to="/admin" title={t("home.card.admin.openAdmin")}>
                  <AdminPanelSettingsOutlinedIcon sx={{ fontSize: "1.1rem" }} />
                </CursorIconAction>
                <CursorIconAction component={Link} to="/admin/benchmarks" title={t("home.card.admin.benchmarks")}>
                  <AssessmentOutlinedIcon sx={{ fontSize: "1.1rem" }} />
                </CursorIconAction>
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
          <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: "rgba(255,255,255,0.9)", mb: 1.25 }}>
            {t("home.recentWorks.title")}
          </Typography>
          {recentWorks.length === 0 ? (
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("home.recentWorks.empty")}</Typography>
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
                  <CursorIconAction
                    component={Link}
                    to={`/workspace?work_id=${encodeURIComponent(item.workId)}`}
                    title={t("home.recentWorks.open")}
                  >
                    <HubOutlinedIcon sx={{ fontSize: "1.1rem" }} />
                  </CursorIconAction>
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
          <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: "rgba(255,255,255,0.9)", mb: 1.25 }}>
            {t("home.session.title")}
          </Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)", lineHeight: 1.6 }}>
            {t("home.session.lastContext")}{" "}
            {status.hasLastWork ? t("home.session.savedLocally") : t("home.session.notSaved")}
          </Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)", lineHeight: 1.6 }}>
            {t("home.session.recentHistory")}{" "}
            {status.hasRecentWorks ? t("home.session.available") : t("home.session.empty")}
          </Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)", lineHeight: 1.6 }}>
            {t("home.session.continueFlow")}{" "}
            {status.hasLocalState ? t("home.session.readyResume") : t("home.session.startsWorkspaces")}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}
