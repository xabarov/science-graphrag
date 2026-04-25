import React from "react";
import { Link } from "react-router-dom";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import { CursorPrimaryButton, CursorSmallButton } from "../common/index.js";

const inputSx = {
  "& .MuiInputBase-input": { fontSize: "0.8125rem" },
  "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
};

export function AskSessionControls(props) {
  const {
    t,
    query,
    onQueryChange,
    workId,
    onWorkIdChange,
    workOptions,
    topK,
    onTopKChange,
    retrievalLabVisible,
    retrievalMode,
    onRetrievalModeChange,
    loading,
    onSubmit,
    inWorkspace,
    standaloneAskPath,
    locked,
    serverSync,
    onServerSyncChange,
    activeSessionId,
    sessionList,
    onActiveSessionChange,
    sessionTitleDraft,
    onSessionTitleDraftChange,
    onSessionTitleCommit,
    onNewSession,
    history,
    onRestoreFromHistory,
    standaloneMode,
    onUrlSyncSupported,
  } = props;

  return (
    <>
      <Box sx={{ mb: 2, p: 1.5, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#1a1a1a" }}>
        <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.9)" }}>{t("askPanel.session.title")}</Typography>
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.35, mb: 1 }}>
          {standaloneMode ? t("askPanel.session.hintStandalone") : t("askPanel.session.hintWorkspace")}
          {serverSync ? <Box component="span" sx={{ display: "block", mt: 0.5 }}>{t("askPanel.session.serverSyncLine")}</Box> : null}
          {onUrlSyncSupported ? <Box component="span" sx={{ display: "block", mt: 0.5 }}>{t("askPanel.session.urlLine")}</Box> : null}
        </Typography>
        <FormControlLabel sx={{ mb: 1, "& .MuiFormControlLabel-label": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.7)" } }} control={<Switch size="small" checked={serverSync} onChange={(_e, v) => onServerSyncChange(v)} />} label={t("askPanel.serverSyncLabel")} />
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "flex-end" }}>
          <FormControl size="small" sx={{ minWidth: 200, flex: "1 1 180px" }}>
            <InputLabel id="ask-session-select-label">{t("askPanel.session.selectLabel")}</InputLabel>
            <Select labelId="ask-session-select-label" label={t("askPanel.session.selectLabel")} value={activeSessionId || ""} onChange={(e) => onActiveSessionChange(String(e.target.value))} sx={{ fontSize: "0.8125rem" }}>
              {sessionList.map((s) => <MenuItem key={s.id} value={s.id} sx={{ fontSize: "0.8125rem" }}>{s.title}</MenuItem>)}
            </Select>
          </FormControl>
          <TextField label={t("askPanel.sessionTitle")} value={sessionTitleDraft} onChange={(ev) => onSessionTitleDraftChange(ev.target.value)} onBlur={onSessionTitleCommit} size="small" sx={{ ...inputSx, flex: "2 1 220px" }} />
          <CursorSmallButton type="button" onClick={onNewSession}>{t("askPanel.newSession")}</CursorSmallButton>
        </Box>
      </Box>

      <Box component="form" onSubmit={onSubmit} sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
        <TextField label={t("askPanel.query")} value={query} onChange={(ev) => onQueryChange(ev.target.value)} multiline minRows={2} fullWidth size="small" sx={inputSx} />
        {!locked ? (
          <Autocomplete freeSolo options={workOptions} getOptionLabel={(opt) => (typeof opt === "string" ? opt : `${(opt.title || "").slice(0, 80) || opt.work_id} (${opt.work_id})`)} inputValue={workId} onInputChange={(_e, v) => onWorkIdChange(v)} onChange={(_e, opt) => opt && typeof opt === "object" && opt.work_id && onWorkIdChange(String(opt.work_id))} renderInput={(params) => <TextField {...params} label={t("askPanel.workIdAutocomplete")} size="small" sx={inputSx} />} />
        ) : null}
        <TextField label={t("askPanel.topK")} value={topK} onChange={(ev) => onTopKChange(ev.target.value)} fullWidth size="small" sx={inputSx} />
        {retrievalLabVisible ? (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>{t("askPanel.retrieval.modeLabel")}</Typography>
            <ToggleButtonGroup exclusive size="small" value={retrievalMode} onChange={(_e, v) => v != null && onRetrievalModeChange(v)} sx={{ alignSelf: "flex-start", "& .MuiToggleButton-root": { fontSize: "0.75rem", py: 0.35, px: 1, color: "rgba(255,255,255,0.55)", borderColor: "rgba(255,255,255,0.12)" }, "& .Mui-selected": { color: "rgba(129,140,248,0.95)", backgroundColor: "rgba(99,102,241,0.12)" } }}>
              <ToggleButton value="vector">{t("askPanel.retrieval.vector")}</ToggleButton>
              <ToggleButton value="hybrid">{t("askPanel.retrieval.hybrid")}</ToggleButton>
              <ToggleButton value="agent">{t("askPanel.retrieval.agent")}</ToggleButton>
            </ToggleButtonGroup>
          </Box>
        ) : null}
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
          <CursorPrimaryButton type="submit" disabled={loading}>{loading ? t("askPanel.runQueryLoading") : t("askPanel.runQuery")}</CursorPrimaryButton>
          {inWorkspace ? <CursorSmallButton component={Link} to={standaloneAskPath} sx={{ textDecoration: "none" }}>{t("askPanel.openStandaloneAsk")}</CursorSmallButton> : null}
        </Box>
      </Box>

      {history.length > 0 ? (
        <Box sx={{ mt: 2, mb: 2, p: 1.5, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#1a1a1a" }}>
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.9)" }}>{standaloneMode ? t("askPanel.recent.standalone") : t("askPanel.recent.workspace")}</Typography>
          <Box sx={{ mt: 1, display: "flex", flexDirection: "column", gap: 0.75 }}>
            {history.slice(0, 3).map((item) => <Box key={item.id} sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 1, flexWrap: "wrap" }}><Box sx={{ minWidth: 0 }}><Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.82)" }}>{item.query}</Typography><Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.25 }}>{item.workId ? `${item.workId} · ` : t("askPanel.recent.globalLine")}{t("askPanel.recent.topK", { k: String(item.topK), count: String(item.citationCount) })}</Typography></Box><CursorSmallButton type="button" onClick={() => onRestoreFromHistory(item)}>{t("askPanel.restore")}</CursorSmallButton></Box>)}
          </Box>
        </Box>
      ) : null}
    </>
  );
}
