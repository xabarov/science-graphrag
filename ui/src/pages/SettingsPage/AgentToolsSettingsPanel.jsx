import React, { useCallback, useEffect, useMemo, useState } from "react";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { useTheme } from "@mui/material/styles";

import { CursorButton, CursorPrimaryButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { outlinedAppTextFieldSx, settingsCardSx } from "../../theme/settingsFormSx.js";

const PDF_READING_MODES = new Set(["off", "ask", "auto_safe_oa"]);
const PDF_READ_BACKEND_MODES = new Set(["pypdf", "vl", "hybrid"]);
const SOURCE_KEYS = ["crossref", "arxiv", "unpaywall", "openalex", "semantic_scholar"];
const TESTABLE_SOURCE_IDS = new Set(["openalex", "semantic_scholar", "mcp"]);

function parseMcpDenylistText(raw) {
  return String(raw ?? "")
    .split(/[\n,]+/)
    .map((s) => s.trim().slice(0, 64))
    .filter(Boolean)
    .slice(0, 32);
}

function formatMcpDenylistText(list) {
  if (!Array.isArray(list) || list.length === 0) return "";
  return list.map((x) => String(x).trim()).filter(Boolean).join("\n");
}

function normalizePdfMode(raw) {
  const s = String(raw ?? "").trim();
  return PDF_READING_MODES.has(s) ? s : "ask";
}

function normalizePdfReadBackend(raw) {
  const s = String(raw ?? "").trim();
  return PDF_READ_BACKEND_MODES.has(s) ? s : "hybrid";
}

/** Parses a number from controlled input; keeps ``fallback`` on empty or non-finite. */
function parseFiniteNumber(raw, fallback) {
  if (raw === "" || raw === null || raw === undefined) return fallback;
  const n = Number(raw);
  return Number.isFinite(n) ? n : fallback;
}

function buildDraft(agentTools) {
  const e = agentTools?.effective || {};
  const src = e.resolved_external_research_sources || {};
  const sup = parseFiniteNumber(e.resolved_agent_supervisor_max_rounds, 10);
  const extTo = parseFiniteNumber(e.resolved_agent_external_http_timeout_seconds, 25);
  const maxCalls = parseFiniteNumber(e.resolved_agent_external_max_calls_per_turn, 8);
  const maxCards = parseFiniteNumber(e.resolved_agent_external_max_source_cards, 24);
  const pdfToolEnabled = Boolean(e.resolved_agent_pdf_read_tool_enabled ?? true);
  const pdfMaxBytes = parseFiniteNumber(e.resolved_agent_pdf_read_max_bytes, 8000000);
  const pdfMaxPages = parseFiniteNumber(e.resolved_agent_pdf_read_max_pages, 30);
  const pdfCacheTtl = parseFiniteNumber(e.resolved_agent_pdf_read_cache_ttl_seconds, 300);
  const pdfCacheMaxEntries = parseFiniteNumber(e.resolved_agent_pdf_read_cache_max_entries, 256);
  const pdfDurable = Boolean(e.resolved_agent_pdf_read_durable_cache_enabled ?? true);
  const mcpTimeout = parseFiniteNumber(e.resolved_agent_mcp_request_timeout_seconds, 15);
  const denylistEffective = e.resolved_agent_mcp_server_denylist;
  const denylistPersisted = agentTools?.agent_mcp_server_denylist;
  const denylistSeed = Array.isArray(denylistPersisted)
    ? denylistPersisted
    : Array.isArray(denylistEffective)
      ? denylistEffective
      : [];
  return {
    externalResearchDefault: Boolean(e.resolved_external_research_default_enabled),
    sources: {
      crossref: src.crossref !== false,
      arxiv: src.arxiv !== false,
      unpaywall: src.unpaywall !== false,
      openalex: src.openalex !== false,
      semantic_scholar: src.semantic_scholar !== false,
    },
    agentUnpaywallOaToolEnabled: Boolean(e.resolved_agent_unpaywall_oa_tool_enabled),
    pdfReadingMode: normalizePdfMode(e.resolved_pdf_reading_mode),
    agentPdfReadBackendMode: normalizePdfReadBackend(e.resolved_agent_pdf_read_backend_mode),
    agentSupervisorMaxRounds: sup,
    agentExternalHttpTimeoutSeconds: extTo,
    agentExternalMaxCallsPerTurn: maxCalls,
    agentExternalMaxSourceCards: maxCards,
    agentPdfReadToolEnabled: pdfToolEnabled,
    agentPdfReadMaxBytes: pdfMaxBytes,
    agentPdfReadMaxPages: pdfMaxPages,
    agentPdfReadCacheTtlSeconds: pdfCacheTtl,
    agentPdfReadCacheMaxEntries: pdfCacheMaxEntries,
    agentPdfReadDurableCacheEnabled: pdfDurable,
    agentMcpRequestTimeoutSeconds: mcpTimeout,
    agentMcpServerDenylistText: formatMcpDenylistText(denylistSeed),
    agentMcpHttpBaseUrl: String(agentTools?.agent_mcp_http_base_url ?? ""),
  };
}

/**
 * @param {object} props
 * @param {object | null | undefined} props.agentTools
 * @param {boolean} props.saving
 * @param {string} props.saveError
 * @param {(payload: Record<string, unknown>) => Promise<void>} props.onSave
 * @param {(dirty: boolean) => void} props.onDirtyChange
 */
export default function AgentToolsSettingsPanel({
  agentTools,
  saving,
  saveError,
  onSave,
  onDirtyChange,
  onTestSource,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const cardSx = useMemo(() => settingsCardSx(tk), [tk]);
  const fieldSx = useMemo(() => outlinedAppTextFieldSx(tk), [tk]);
  const insetSx = useMemo(
    () => ({
      border: `1px solid ${tk.border.default}`,
      backgroundColor: tk.control.outlinedBg,
      borderRadius: 1,
      padding: 1.25,
    }),
    [tk],
  );
  const syncKey = useMemo(() => JSON.stringify(agentTools ?? null), [agentTools]);
  const [draft, setDraft] = useState(() => buildDraft(agentTools));
  const [baselineJson, setBaselineJson] = useState(() => JSON.stringify(buildDraft(agentTools)));
  const [sourceTesting, setSourceTesting] = useState("");
  const [sourceTestError, setSourceTestError] = useState("");

  const emailStatusKey = useMemo(() => {
    const raw = String(agentTools?.credentials?.research_contact_email_status || "unknown");
    if (raw === "configured") return "settings.agentTools.emailStatus.configured";
    if (raw === "not_configured") return "settings.agentTools.emailStatus.not_configured";
    return "settings.agentTools.emailStatus.unknown";
  }, [agentTools?.credentials?.research_contact_email_status]);

  const semanticScholarKeyStatusLabel = useMemo(() => {
    const raw = String(agentTools?.credentials?.semantic_scholar_api_key_status || "unknown");
    if (raw === "configured") return t("settings.agentTools.emailStatus.configured");
    if (raw === "not_configured") return t("settings.agentTools.emailStatus.not_configured");
    return t("settings.agentTools.emailStatus.unknown");
  }, [agentTools?.credentials?.semantic_scholar_api_key_status, t]);

  const mcpOperatorState = String(agentTools?.integrations?.mcp_operator_state || "disabled");

  const mcpStateLabel = useMemo(() => {
    const key = `settings.agentTools.mcpState.${mcpOperatorState}`;
    const out = t(key);
    return out !== key ? out : mcpOperatorState;
  }, [mcpOperatorState, t]);

  const pdfDurableStatusLabel = useMemo(() => {
    const raw = String(agentTools?.credentials?.pdf_read_durable_cache || "disabled_no_redis");
    const key = `settings.agentTools.pdfDurableStatus.${raw}`;
    const out = t(key);
    return out !== key ? out : raw;
  }, [agentTools?.credentials?.pdf_read_durable_cache, t]);

  /* eslint-disable react-hooks/set-state-in-effect -- hydrate when server snapshot changes */
  useEffect(() => {
    const next = buildDraft(agentTools);
    const serialized = JSON.stringify(next);
    setDraft(next);
    setBaselineJson(serialized);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- content hash only
  }, [syncKey]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const dirty = useMemo(() => JSON.stringify(draft) !== baselineJson, [baselineJson, draft]);

  useEffect(() => {
    onDirtyChange?.(dirty);
  }, [dirty, onDirtyChange]);

  const sourcesSnapshot = Array.isArray(agentTools?.sources) ? agentTools.sources : [];

  const tierLabel = useCallback(
    (row) => {
      const tier = String(row?.tier || "");
      const key = `settings.agentTools.tier.${tier}`;
      const out = t(key);
      return out !== key ? out : tier;
    },
    [t],
  );

  const statusLabel = useCallback(
    (row) => {
      const st = String(row?.status || "");
      const key = `settings.agentTools.status.${st}`;
      const out = t(key);
      return out !== key ? out : st;
    },
    [t],
  );

  const sourceNameLabel = useCallback(
    (key) => {
      const out = t(`settings.agentTools.sourceName.${key}`);
      return out !== `settings.agentTools.sourceName.${key}` ? out : key;
    },
    [t],
  );

  const sourceToolLabel = useCallback(
    (key) => {
      const out = t(`settings.agentTools.sourceTools.${key}`);
      return out !== `settings.agentTools.sourceTools.${key}` ? out : "";
    },
    [t],
  );

  async function handleSubmit(event) {
    event.preventDefault();
    if (!dirty) return;
    const payload = {
      external_research_default_enabled: draft.externalResearchDefault,
      external_research_sources: { ...draft.sources },
      pdf_reading_mode: draft.pdfReadingMode,
      agent_pdf_read_backend_mode: draft.agentPdfReadBackendMode,
      agent_unpaywall_oa_tool_enabled: draft.agentUnpaywallOaToolEnabled,
      agent_supervisor_max_rounds: Math.max(
        2,
        Math.min(32, Math.trunc(parseFiniteNumber(draft.agentSupervisorMaxRounds, 10))),
      ),
      agent_external_http_timeout_seconds: Math.max(
        5,
        Math.min(120, parseFiniteNumber(draft.agentExternalHttpTimeoutSeconds, 25)),
      ),
      agent_external_max_calls_per_turn: Math.max(
        1,
        Math.min(32, Math.trunc(parseFiniteNumber(draft.agentExternalMaxCallsPerTurn, 8))),
      ),
      agent_external_max_source_cards: Math.max(
        4,
        Math.min(128, Math.trunc(parseFiniteNumber(draft.agentExternalMaxSourceCards, 24))),
      ),
      agent_pdf_read_tool_enabled: Boolean(draft.agentPdfReadToolEnabled),
      agent_pdf_read_max_bytes: Math.max(
        100000,
        Math.min(100000000, Math.trunc(parseFiniteNumber(draft.agentPdfReadMaxBytes, 8000000))),
      ),
      agent_pdf_read_max_pages: Math.max(
        1,
        Math.min(500, Math.trunc(parseFiniteNumber(draft.agentPdfReadMaxPages, 30))),
      ),
      agent_pdf_read_cache_ttl_seconds: Math.max(
        0,
        Math.min(86400, Math.trunc(parseFiniteNumber(draft.agentPdfReadCacheTtlSeconds, 300))),
      ),
      agent_pdf_read_cache_max_entries: Math.max(
        16,
        Math.min(10000, Math.trunc(parseFiniteNumber(draft.agentPdfReadCacheMaxEntries, 256))),
      ),
      agent_pdf_read_durable_cache_enabled: Boolean(draft.agentPdfReadDurableCacheEnabled),
      agent_mcp_request_timeout_seconds: Math.max(
        1,
        Math.min(120, parseFiniteNumber(draft.agentMcpRequestTimeoutSeconds, 15)),
      ),
      agent_mcp_server_denylist: parseMcpDenylistText(draft.agentMcpServerDenylistText),
      agent_mcp_http_base_url: String(draft.agentMcpHttpBaseUrl || "").trim(),
    };
    await onSave(payload);
  }

  async function handleTestSource(sourceId) {
    if (!onTestSource) return;
    setSourceTesting(sourceId);
    setSourceTestError("");
    try {
      await onTestSource(sourceId);
    } catch (error) {
      setSourceTestError(String(error?.message || error || "source test failed"));
    } finally {
      setSourceTesting("");
    }
  }

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
      <Box sx={{ ...cardSx, padding: 1.5 }}>
        <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "flex-start", justifyContent: "space-between", gap: 1.5 }}>
          <Box sx={{ minWidth: 260, flex: "1 1 420px" }}>
            <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>
              {t("settings.agentTools.title")}
            </Typography>
            <Typography sx={{ marginTop: 0.5, fontSize: "0.78rem", color: tk.text.secondary, lineHeight: 1.5 }}>
              {t("settings.agentTools.intro")}
            </Typography>
          </Box>
          <CursorPrimaryButton type="submit" disabled={!dirty || saving}>
            {saving ? t("settings.agentTools.saveSaving") : t("settings.agentTools.save")}
          </CursorPrimaryButton>
        </Box>
      </Box>

      <Box sx={{ ...cardSx, padding: 1.5 }}>
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", xl: "minmax(360px, 0.9fr) minmax(420px, 1.1fr)" }, gap: 1.5 }}>
          <Box>
            <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>
              {t("settings.agentTools.researchCardTitle")}
            </Typography>
            <Typography sx={{ marginTop: 0.5, fontSize: "0.78rem", color: tk.text.secondary, lineHeight: 1.5 }}>
              {t("settings.agentTools.researchCardHint")}
            </Typography>

            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75, marginTop: 1.25 }}>
              <FormControlLabel
                sx={{ ...insetSx, margin: 0, alignItems: "flex-start" }}
                control={
                  <Switch
                    checked={draft.externalResearchDefault}
                    onChange={(_e, v) => setDraft((d) => ({ ...d, externalResearchDefault: v }))}
                    size="small"
                  />
                }
                label={
                  <Box>
                    <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary }}>
                      {t("settings.agentTools.externalDefaultLabel")}
                    </Typography>
                    <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, marginTop: 0.25 }}>
                      {t("settings.agentTools.externalDefaultHint")}
                    </Typography>
                  </Box>
                }
              />

              <Box sx={insetSx}>
                <Typography sx={{ marginBottom: 0.5, fontSize: "0.72rem", fontWeight: 600, color: tk.text.secondary }}>
                  {t("settings.agentTools.operatorSources")}
                </Typography>
                <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 0.5 }}>
                  {SOURCE_KEYS.map((key) => (
                    <FormControlLabel
                      key={key}
                      sx={{
                        margin: 0,
                        minWidth: 0,
                        alignItems: "flex-start",
                        border: `1px solid ${tk.border.default}`,
                        borderRadius: 1,
                        padding: "0.45rem 0.5rem",
                        backgroundColor: "rgba(255,255,255,0.018)",
                        "& .MuiFormControlLabel-label": { minWidth: 0, flex: 1 },
                      }}
                      control={
                        <Switch
                          checked={Boolean(draft.sources[key])}
                          onChange={(_e, v) =>
                            setDraft((d) => ({
                              ...d,
                              sources: { ...d.sources, [key]: v },
                            }))
                          }
                          size="small"
                        />
                      }
                      label={
                        <Box sx={{ minWidth: 0, paddingTop: 0.1 }}>
                          <Typography sx={{ fontSize: "0.78rem", fontWeight: 600, color: tk.text.primary }}>
                            {sourceNameLabel(key)}
                          </Typography>
                          <Typography sx={{ marginTop: 0.1, fontSize: "0.68rem", color: tk.text.muted, lineHeight: 1.3, overflowWrap: "anywhere" }}>
                            {sourceToolLabel(key)}
                          </Typography>
                        </Box>
                      }
                    />
                  ))}
                </Box>
              </Box>

              <FormControlLabel
                sx={{ ...insetSx, margin: 0, alignItems: "flex-start" }}
                control={
                  <Switch
                    checked={draft.agentUnpaywallOaToolEnabled}
                    onChange={(_e, v) => setDraft((d) => ({ ...d, agentUnpaywallOaToolEnabled: v }))}
                    size="small"
                  />
                }
                label={
                  <Box>
                    <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary }}>
                      {t("settings.agentTools.unpaywallGateLabel")}
                    </Typography>
                    <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, marginTop: 0.25 }}>
                      {t("settings.agentTools.unpaywallGateHint")}
                    </Typography>
                  </Box>
                }
              />
            </Box>
          </Box>

          <Box>
            <Typography sx={{ fontSize: "0.75rem", fontWeight: 600, color: tk.text.secondary }}>
              {t("settings.agentTools.sourceStatusTitle")}
            </Typography>
            <Box sx={{ display: "flex", flexDirection: "column", marginTop: 0.75, border: `1px solid ${tk.border.default}`, borderRadius: 1, overflow: "hidden" }}>
              {sourcesSnapshot.map((row) => (
                <Box
                  key={row.id}
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", sm: "minmax(150px, 1fr) auto" },
                    alignItems: "center",
                    gap: 0.75,
                    borderBottom: `1px solid ${tk.border.default}`,
                    padding: "0.55rem 0.75rem",
                    "&:last-of-type": { borderBottom: 0 },
                  }}
                >
                  <Typography sx={{ minWidth: 0, fontSize: "0.8125rem", fontWeight: 500, color: tk.text.primary, overflowWrap: "anywhere" }}>
                    {row.label || row.id}
                  </Typography>
                  <Box sx={{ display: "flex", flexWrap: "wrap", justifyContent: { xs: "flex-start", sm: "flex-end" }, gap: 0.5, minWidth: 0 }}>
                    <Chip size="small" label={tierLabel(row)} variant="outlined" sx={{ fontSize: "0.7rem", maxWidth: "100%" }} />
                    <Chip size="small" label={statusLabel(row)} variant="outlined" sx={{ fontSize: "0.7rem", maxWidth: "100%" }} />
                    {TESTABLE_SOURCE_IDS.has(String(row.id || "")) ? (
                      <CursorButton
                        type="button"
                        size="small"
                        disabled={Boolean(sourceTesting)}
                        onClick={() => handleTestSource(row.id)}
                      >
                        {sourceTesting === row.id
                          ? t("settings.agentTools.testRunning")
                          : t("settings.agentTools.testButton")}
                      </CursorButton>
                    ) : null}
                  </Box>
                  {row.last_test ? (
                    <Typography sx={{ gridColumn: "1 / -1", fontSize: "0.72rem", color: tk.text.muted }}>
                      {t("settings.agentTools.lastTest", { at: String(row.last_test) })}
                    </Typography>
                  ) : null}
                  {row.last_error ? (
                    <Typography sx={{ gridColumn: "1 / -1", fontSize: "0.72rem", color: tk.state.dangerFg, overflowWrap: "anywhere" }}>
                      {String(row.last_error)}
                    </Typography>
                  ) : null}
                </Box>
              ))}
            </Box>
            {sourceTestError ? (
              <Typography sx={{ marginTop: 0.75, fontSize: "0.72rem", color: tk.state.dangerFg }}>
                {sourceTestError}
              </Typography>
            ) : null}
          </Box>
        </Box>
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "repeat(3, minmax(0, 1fr))" }, gap: 1.5 }}>
        <Box sx={{ ...cardSx, padding: 1.5 }}>
          <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>
            {t("settings.agentTools.pdfCardTitle")}
          </Typography>
          <Typography sx={{ marginTop: 0.75, fontSize: "0.78rem", color: tk.text.secondary, lineHeight: 1.55 }}>
            {t("settings.agentTools.pdfCardHint")}
          </Typography>
          <Box sx={{ marginTop: 1.5, maxWidth: 420 }}>
            <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, marginBottom: 0.75 }}>
              {t("settings.agentTools.pdfModeLabel")}
            </Typography>
            <Select
              size="small"
              fullWidth
              value={draft.pdfReadingMode}
              onChange={(e) => setDraft((d) => ({ ...d, pdfReadingMode: normalizePdfMode(e.target.value) }))}
              inputProps={{ "aria-label": t("settings.agentTools.pdfModeLabel") }}
            >
              <MenuItem value="off">{t("settings.agentTools.pdfMode.off")}</MenuItem>
              <MenuItem value="ask">{t("settings.agentTools.pdfMode.ask")}</MenuItem>
              <MenuItem value="auto_safe_oa">{t("settings.agentTools.pdfMode.auto")}</MenuItem>
            </Select>
            <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, marginBottom: 0.75, marginTop: 1.5 }}>
              {t("settings.agentTools.pdfBackendLabel")}
            </Typography>
            <Select
              size="small"
              fullWidth
              value={draft.agentPdfReadBackendMode}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  agentPdfReadBackendMode: normalizePdfReadBackend(e.target.value),
                }))
              }
              inputProps={{ "aria-label": t("settings.agentTools.pdfBackendLabel") }}
            >
              <MenuItem value="pypdf">{t("settings.agentTools.pdfBackend.pypdf")}</MenuItem>
              <MenuItem value="vl">{t("settings.agentTools.pdfBackend.vl")}</MenuItem>
              <MenuItem value="hybrid">{t("settings.agentTools.pdfBackend.hybrid")}</MenuItem>
            </Select>
            <FormControlLabel
              sx={{ mt: 1, ml: 0 }}
              control={
                <Switch
                  checked={Boolean(draft.agentPdfReadToolEnabled)}
                  onChange={(_e, v) => setDraft((d) => ({ ...d, agentPdfReadToolEnabled: v }))}
                  size="small"
                />
              }
              label={t("settings.agentTools.pdfToolEnabledLabel")}
            />
            <FormControlLabel
              sx={{ mt: 1, ml: 0 }}
              control={
                <Switch
                  checked={Boolean(draft.agentPdfReadDurableCacheEnabled)}
                  onChange={(_e, v) => setDraft((d) => ({ ...d, agentPdfReadDurableCacheEnabled: v }))}
                  size="small"
                />
              }
              label={t("settings.agentTools.pdfDurableCacheLabel")}
            />
          </Box>
        </Box>

        <Box sx={{ ...cardSx, padding: 1.5 }}>
          <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>
            {t("settings.agentTools.integrationsTitle")}
          </Typography>
          <Typography sx={{ marginTop: 0.75, fontSize: "0.78rem", color: tk.text.secondary, lineHeight: 1.55 }}>
            {t("settings.agentTools.integrationsHint")}
          </Typography>
          <Box sx={{ marginTop: 1.25, display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1 }}>
            <Chip
              size="small"
              label={mcpStateLabel}
              sx={{
                height: 22,
                fontSize: "0.75rem",
                backgroundColor: tk.control.outlinedBg,
                border: `1px solid ${tk.border.default}`,
              }}
            />
            <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted }}>
              {t("settings.agentTools.mcpAuthModel")}
            </Typography>
          </Box>
          <Box sx={{ marginTop: 1.25, fontSize: "0.8125rem", color: tk.text.secondary, lineHeight: 1.6 }}>
            <div>
              {t("settings.agentTools.mcpEnabled", {
                value: agentTools?.integrations?.mcp_tools_enabled
                  ? t("settings.agentTools.commonYes")
                  : t("settings.agentTools.commonNo"),
              })}
            </div>
            <div>
              {t("settings.agentTools.mcpUrlConfigured", {
                value: agentTools?.integrations?.mcp_http_base_url_configured
                  ? t("settings.agentTools.commonYes")
                  : t("settings.agentTools.commonNo"),
              })}
            </div>
            <div>
              {t("settings.agentTools.mcpAdapterHost", {
                host:
                  agentTools?.integrations?.mcp_base_url_host ||
                  t("settings.agentTools.mcpAdapterHostUnset"),
              })}
            </div>
            <div>
              {t("settings.agentTools.mcpTimeoutEffective", {
                seconds: Number(agentTools?.integrations?.mcp_request_timeout_seconds || 15),
              })}
            </div>
            <div>
              {t("settings.agentTools.mcpDenylist", {
                n: Number(agentTools?.integrations?.mcp_server_denylist_count || 0),
              })}
            </div>
            <div>
              {t("settings.agentTools.mcpAdapterSource", {
                value:
                  String(agentTools?.integrations?.mcp_adapter_url_source || "environment") === "settings"
                    ? t("settings.agentTools.mcpAdapterSourceSettings")
                    : t("settings.agentTools.mcpAdapterSourceEnvironment"),
              })}
            </div>
            <Typography sx={{ marginTop: 0.5, fontSize: "0.72rem", color: tk.text.muted }}>
              {t("settings.agentTools.mcpAdapterUrlSource")}
            </Typography>
            {agentTools?.integrations?.mcp_last_test ? (
              <Typography sx={{ marginTop: 0.5, fontSize: "0.72rem", color: tk.text.muted }}>
                {t("settings.agentTools.lastTest", { at: String(agentTools.integrations.mcp_last_test) })}
              </Typography>
            ) : null}
            {agentTools?.integrations?.mcp_last_error ? (
              <Typography sx={{ marginTop: 0.35, fontSize: "0.72rem", color: tk.state.dangerFg, overflowWrap: "anywhere" }}>
                {String(agentTools.integrations.mcp_last_error)}
              </Typography>
            ) : null}
          </Box>
          <Accordion
            disableGutters
            elevation={0}
            sx={{
              marginTop: 1.25,
              border: `1px solid ${tk.border.default}`,
              borderRadius: 1,
              backgroundColor: tk.control.outlinedBg,
              "&:before": { display: "none" },
            }}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ fontSize: "1rem" }} />}>
              <Typography sx={{ fontSize: "0.78rem", fontWeight: 600, color: tk.text.primary }}>
                {t("settings.agentTools.mcpAdvancedTitle")}
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 1.25 }}>
                <TextField
                  label={t("settings.agentTools.mcpAdapterUrl")}
                  size="small"
                  value={draft.agentMcpHttpBaseUrl || ""}
                  onChange={(e) =>
                    setDraft((d) => ({
                      ...d,
                      agentMcpHttpBaseUrl: e.target.value,
                    }))
                  }
                  helperText={t("settings.agentTools.mcpAdapterUrlHint")}
                  inputProps={{ "aria-label": t("settings.agentTools.mcpAdapterUrl") }}
                  sx={fieldSx}
                />
                <TextField
                  label={t("settings.agentTools.mcpRequestTimeout")}
                  type="number"
                  size="small"
                  value={draft.agentMcpRequestTimeoutSeconds}
                  onChange={(e) =>
                    setDraft((d) => ({
                      ...d,
                      agentMcpRequestTimeoutSeconds: parseFiniteNumber(
                        e.target.value,
                        d.agentMcpRequestTimeoutSeconds,
                      ),
                    }))
                  }
                  inputProps={{
                    min: 1,
                    max: 120,
                    step: 0.5,
                    "aria-label": t("settings.agentTools.mcpRequestTimeout"),
                  }}
                  sx={fieldSx}
                />
                <TextField
                  label={t("settings.agentTools.mcpDenylistField")}
                  size="small"
                  multiline
                  minRows={2}
                  maxRows={6}
                  inputProps={{ "aria-label": t("settings.agentTools.mcpDenylistField") }}
                  value={draft.agentMcpServerDenylistText}
                  onChange={(e) =>
                    setDraft((d) => ({ ...d, agentMcpServerDenylistText: e.target.value }))
                  }
                  helperText={t("settings.agentTools.mcpDenylistHint")}
                  sx={fieldSx}
                />
                <Box sx={{ display: "flex", justifyContent: "flex-start" }}>
                  <CursorButton
                    type="button"
                    size="small"
                    disabled={Boolean(sourceTesting)}
                    onClick={() => handleTestSource("mcp")}
                  >
                    {sourceTesting === "mcp" ? t("settings.agentTools.testRunning") : t("settings.agentTools.testMcpButton")}
                  </CursorButton>
                </Box>
              </Box>
            </AccordionDetails>
          </Accordion>
        </Box>

        <Box sx={{ ...cardSx, padding: 1.5 }}>
          <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>
            {t("settings.agentTools.credentialsTitle")}
          </Typography>
          <Typography sx={{ marginTop: 0.75, fontSize: "0.8125rem", color: tk.text.secondary }}>
            {t("settings.agentTools.credentialsMailto", {
              status: t(emailStatusKey),
            })}
          </Typography>
          <Typography sx={{ marginTop: 1, fontSize: "0.8125rem", color: tk.text.secondary }}>
            {t("settings.agentTools.credentialsSemanticScholar", { status: semanticScholarKeyStatusLabel })}
          </Typography>
          <Typography sx={{ marginTop: 0.75, fontSize: "0.8125rem", color: tk.text.secondary }}>
            {t("settings.agentTools.credentialsPdfDurable", { status: pdfDurableStatusLabel })}
          </Typography>
          <Typography sx={{ marginTop: 1, fontSize: "0.72rem", color: tk.text.muted, lineHeight: 1.55 }}>
            {t("settings.agentTools.credentialsHint")}
          </Typography>
        </Box>
      </Box>

      <Accordion disableGutters elevation={0} sx={{ border: `1px solid ${tk.border.default}`, borderRadius: 1, backgroundColor: tk.surface.panel, "&:before": { display: "none" } }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ fontSize: "1.1rem" }} />}>
          <Typography sx={{ fontSize: "0.8125rem", fontWeight: 600, color: tk.text.primary }}>
            {t("settings.agentTools.advancedTitle")}
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
            <TextField
              label={t("settings.agentTools.supervisorRounds")}
              type="number"
              size="small"
              value={draft.agentSupervisorMaxRounds}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  agentSupervisorMaxRounds: parseFiniteNumber(e.target.value, d.agentSupervisorMaxRounds),
                }))
              }
              inputProps={{ min: 2, max: 32 }}
              sx={fieldSx}
            />
            <TextField
              label={t("settings.agentTools.externalHttpTimeout")}
              type="number"
              size="small"
              value={draft.agentExternalHttpTimeoutSeconds}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  agentExternalHttpTimeoutSeconds: parseFiniteNumber(
                    e.target.value,
                    d.agentExternalHttpTimeoutSeconds,
                  ),
                }))
              }
              inputProps={{ min: 5, max: 120, step: 0.5 }}
              sx={fieldSx}
            />
            <TextField
              label={t("settings.agentTools.maxCallsPerTurn")}
              type="number"
              size="small"
              value={draft.agentExternalMaxCallsPerTurn}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  agentExternalMaxCallsPerTurn: parseFiniteNumber(
                    e.target.value,
                    d.agentExternalMaxCallsPerTurn,
                  ),
                }))
              }
              inputProps={{ min: 1, max: 32 }}
              sx={fieldSx}
            />
            <TextField
              label={t("settings.agentTools.maxSourceCards")}
              type="number"
              size="small"
              value={draft.agentExternalMaxSourceCards}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  agentExternalMaxSourceCards: parseFiniteNumber(
                    e.target.value,
                    d.agentExternalMaxSourceCards,
                  ),
                }))
              }
              inputProps={{ min: 4, max: 128 }}
              sx={fieldSx}
            />
            <TextField
              label={t("settings.agentTools.pdfMaxBytes")}
              type="number"
              size="small"
              value={draft.agentPdfReadMaxBytes}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  agentPdfReadMaxBytes: parseFiniteNumber(
                    e.target.value,
                    d.agentPdfReadMaxBytes,
                  ),
                }))
              }
              inputProps={{ min: 100000, max: 100000000, step: 100000 }}
              sx={fieldSx}
            />
            <TextField
              label={t("settings.agentTools.pdfMaxPages")}
              type="number"
              size="small"
              value={draft.agentPdfReadMaxPages}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  agentPdfReadMaxPages: parseFiniteNumber(
                    e.target.value,
                    d.agentPdfReadMaxPages,
                  ),
                }))
              }
              inputProps={{ min: 1, max: 500 }}
              sx={fieldSx}
            />
            <TextField
              label={t("settings.agentTools.pdfCacheTtl")}
              type="number"
              size="small"
              value={draft.agentPdfReadCacheTtlSeconds}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  agentPdfReadCacheTtlSeconds: parseFiniteNumber(
                    e.target.value,
                    d.agentPdfReadCacheTtlSeconds,
                  ),
                }))
              }
              inputProps={{ min: 0, max: 86400 }}
              sx={fieldSx}
            />
            <TextField
              label={t("settings.agentTools.pdfCacheMaxEntries")}
              type="number"
              size="small"
              value={draft.agentPdfReadCacheMaxEntries}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  agentPdfReadCacheMaxEntries: parseFiniteNumber(
                    e.target.value,
                    d.agentPdfReadCacheMaxEntries,
                  ),
                }))
              }
              inputProps={{ min: 16, max: 10000 }}
              sx={fieldSx}
            />
          </Box>
        </AccordionDetails>
      </Accordion>

      {saveError ? (
        <Alert
          severity="error"
          sx={{
            backgroundColor: tk.control.outlinedBg,
            border: `1px solid ${tk.border.default}`,
            color: tk.text.primary,
            "& .MuiAlert-icon": { color: tk.state.dangerFg },
          }}
        >
          <Typography sx={{ fontSize: "0.8125rem" }}>{saveError}</Typography>
        </Alert>
      ) : null}

    </Box>
  );
}
