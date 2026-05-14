import React, { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import FormControl from "@mui/material/FormControl";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormLabel from "@mui/material/FormLabel";
import Radio from "@mui/material/Radio";
import RadioGroup from "@mui/material/RadioGroup";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

/**
 * Structured multi-choice form for ``user_question_asked`` / ``user_structured_answer`` roundtrip.
 *
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   envelope: { request_id: string, questions: Array<{ id: string, prompt: string, options: Array<{ id: string, label: string }>, allow_multiple?: boolean }> },
 *   onSubmitAnswers: (payload: { request_id: string, answers: Array<{ question_id: string, selected_option_ids: string[] }> }) => void | Promise<void>,
 *   disabled?: boolean,
 * }} props
 */
export default function AskUserQuestionForm({ t, envelope, onSubmitAnswers, disabled = false }) {
  const tk = useTheme().appTokens;
  const questions = useMemo(() => {
    const q = envelope && Array.isArray(envelope.questions) ? envelope.questions : [];
    return q.filter((x) => x && typeof x === "object" && String(x.id || "").trim() && String(x.prompt || "").trim());
  }, [envelope]);

  /** questionId -> selected option id(s) */
  const [selections, setSelections] = useState(() => ({}));

  const requestId = String(envelope?.request_id || "").trim();

  const handleSubmit = () => {
    const answers = questions.map((q) => {
      const qid = String(q.id || "").trim();
      const raw = selections[q.id];
      const ids = Array.isArray(raw) ? raw : raw != null ? [String(raw)] : [];
      return { question_id: qid, selected_option_ids: ids.map(String).filter(Boolean) };
    });
    onSubmitAnswers({ request_id: requestId, answers });
  };

  const allAnswered = questions.every((q) => {
    const v = selections[q.id];
    if (q.allow_multiple) return Array.isArray(v) && v.length > 0;
    return v != null && String(v).trim() !== "";
  });

  return (
    <Box
      sx={{
        my: 1.5,
        p: 1.25,
        borderRadius: "6px",
        border: `1px solid ${tk.border.strong}`,
        backgroundColor: tk.surface.panel,
        maxWidth: "min(640px, 100%)",
      }}
    >
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: tk.text.primary, mb: 1 }}>
        {t("askPanel.userQuestion.title")}
      </Typography>
      {questions.map((q) => (
        <Box key={q.id} sx={{ mb: 1.5 }}>
          <FormControl component="fieldset" variant="standard" fullWidth disabled={disabled}>
            <FormLabel component="legend" sx={{ fontSize: "0.8125rem", color: tk.text.secondary, mb: 0.75 }}>
              {q.prompt}
            </FormLabel>
            {q.allow_multiple ? (
              <Box sx={{ display: "flex", flexDirection: "column", gap: 0.25 }}>
                {(q.options || []).map((opt) => {
                  const oid = String(opt.id ?? "").trim();
                  return (
                    <FormControlLabel
                      key={oid || String(opt.label ?? "")}
                      control={
                        <Checkbox
                          size="small"
                          checked={Boolean((selections[q.id] || []).map(String).includes(oid))}
                          onChange={() => {
                            setSelections((prev) => {
                              const cur = Array.isArray(prev[q.id]) ? [...prev[q.id]] : [];
                              const i = cur.map(String).indexOf(oid);
                              if (i >= 0) cur.splice(i, 1);
                              else cur.push(oid);
                              return { ...prev, [q.id]: cur };
                            });
                          }}
                          sx={{ p: 0.5 }}
                        />
                      }
                      label={<Typography sx={{ fontSize: "0.8125rem" }}>{opt.label}</Typography>}
                    />
                  );
                })}
              </Box>
            ) : (
              <RadioGroup
                value={selections[q.id] != null ? String(selections[q.id]) : ""}
                onChange={(e) => setSelections((prev) => ({ ...prev, [q.id]: e.target.value }))}
              >
                {(q.options || []).map((opt) => {
                  const oid = String(opt.id ?? "").trim();
                  return (
                    <FormControlLabel
                      key={oid || String(opt.label ?? "")}
                      value={oid}
                      control={<Radio size="small" />}
                      label={<Typography sx={{ fontSize: "0.8125rem" }}>{opt.label}</Typography>}
                    />
                  );
                })}
              </RadioGroup>
            )}
          </FormControl>
        </Box>
      ))}
      <Button variant="contained" size="small" disabled={disabled || !allAnswered} onClick={() => void handleSubmit()}>
        {t("askPanel.userQuestion.submit")}
      </Button>
    </Box>
  );
}
