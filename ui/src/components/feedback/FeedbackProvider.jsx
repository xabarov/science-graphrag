import React, { useCallback, useMemo, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Snackbar from "@mui/material/Snackbar";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { CursorButton, CursorDangerButton, CursorPrimaryButton } from "../common/index.js";
import { FeedbackContext } from "./FeedbackContext.js";
import { FeedbackShell } from "./FeedbackShell.jsx";

/** @typedef {{ dialogInstanceId: string, kind: "confirm", title: string, body?: string, confirmLabel?: string, cancelLabel?: string, variant?: "danger" | "default", resolve: (v: boolean) => void }} ConfirmItem */
/** @typedef {{ dialogInstanceId: string, kind: "prompt", title: string, description?: string, label?: string, defaultValue?: string, confirmLabel?: string, cancelLabel?: string, requiredMessage?: string, validate?: (value: string) => string | null, resolve: (v: string | null) => void }} PromptItem */
/** @typedef {ConfirmItem | PromptItem | null} DialogItem */

function nextDialogInstanceId() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/** Prompt dialog fields; remounted via `key={dialog.dialogInstanceId}` when a new prompt opens. */
function PromptDialogBody({ dialog, onResolve, onShellClose }) {
  const [promptValue, setPromptValue] = useState(() => String(dialog.defaultValue ?? ""));
  const [promptError, setPromptError] = useState("");

  const cancelLabel = dialog.cancelLabel || "Cancel";
  const confirmLabel = dialog.confirmLabel || "Save";
  const submit = () => {
    const raw = promptValue;
    if (dialog.validate) {
      const err = dialog.validate(raw);
      if (err) {
        setPromptError(err);
        return;
      }
      onResolve(String(raw).trim());
      return;
    }
    const trimmed = String(raw).trim();
    if (!trimmed) {
      setPromptError(dialog.requiredMessage || "Required");
      return;
    }
    onResolve(trimmed);
  };

  return (
    <FeedbackShell
      open
      onClose={onShellClose}
      title={dialog.title}
      titleId="feedback-prompt-title"
      aria-describedby="feedback-prompt-desc"
      actions={
        <>
          <CursorButton type="button" size="small" onClick={() => onResolve(null)} sx={{ color: "rgba(255,255,255,0.7)" }}>
            {cancelLabel}
          </CursorButton>
          <CursorPrimaryButton type="button" size="small" onClick={submit}>
            {confirmLabel}
          </CursorPrimaryButton>
        </>
      }
    >
      <Box id="feedback-prompt-desc" sx={{ display: "flex", flexDirection: "column", gap: 1.25 }}>
        {dialog.description ? (
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)" }}>{dialog.description}</Typography>
        ) : null}
        <TextField
          label={dialog.label || undefined}
          inputProps={dialog.label ? undefined : { "aria-label": dialog.title }}
          value={promptValue}
          onChange={(e) => {
            setPromptValue(e.target.value);
            if (promptError) setPromptError("");
          }}
          size="small"
          fullWidth
          autoFocus
          error={Boolean(promptError)}
          helperText={promptError || undefined}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              submit();
            }
          }}
          sx={{
            "& .MuiInputBase-input": { fontSize: "0.8125rem" },
            "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
            "& .MuiFormHelperText-root": { fontSize: "0.75rem" },
          }}
        />
      </Box>
    </FeedbackShell>
  );
}

function FeedbackDialogStack({ dialog, onResolve }) {
  if (!dialog) return null;

  const handleShellClose = (_event, reason) => {
    if (reason === "backdropClick" || reason === "escapeKeyDown") {
      if (dialog.kind === "confirm") onResolve(false);
      if (dialog.kind === "prompt") onResolve(null);
    }
  };

  if (dialog.kind === "confirm") {
    const variant = dialog.variant === "danger" ? "danger" : "default";
    const cancelLabel = dialog.cancelLabel || "Cancel";
    const confirmLabel = dialog.confirmLabel || (variant === "danger" ? "Delete" : "OK");
    return (
      <FeedbackShell
        open
        onClose={handleShellClose}
        title={dialog.title}
        titleId="feedback-confirm-title"
        aria-describedby={dialog.body ? "feedback-confirm-desc" : undefined}
        actions={
          <>
            <CursorButton type="button" size="small" onClick={() => onResolve(false)} sx={{ color: "rgba(255,255,255,0.7)" }}>
              {cancelLabel}
            </CursorButton>
            {variant === "danger" ? (
              <CursorDangerButton type="button" size="small" onClick={() => onResolve(true)}>
                {confirmLabel}
              </CursorDangerButton>
            ) : (
              <CursorPrimaryButton type="button" size="small" onClick={() => onResolve(true)}>
                {confirmLabel}
              </CursorPrimaryButton>
            )}
          </>
        }
      >
        {dialog.body ? (
          <Typography id="feedback-confirm-desc" component="span" sx={{ display: "block" }}>
            {dialog.body}
          </Typography>
        ) : null}
      </FeedbackShell>
    );
  }

  if (dialog.kind === "prompt") {
    return (
      <PromptDialogBody key={dialog.dialogInstanceId} dialog={dialog} onResolve={onResolve} onShellClose={handleShellClose} />
    );
  }

  return null;
}

export function FeedbackProvider({ children }) {
  /** @type {React.MutableRefObject<DialogItem[]>} */
  const queueRef = useRef([]);
  const [dialog, setDialog] = useState(/** @type {DialogItem} */ (null));
  const [toast, setToast] = useState({ open: false, message: "", severity: "info" });

  const enqueue = useCallback((item) => {
    setDialog((cur) => {
      if (cur) {
        queueRef.current.push(item);
        return cur;
      }
      return item;
    });
  }, []);

  const resolveAndAdvance = useCallback((value) => {
    setDialog((cur) => {
      if (!cur) return null;
      cur.resolve(value);
      return queueRef.current.shift() || null;
    });
  }, []);

  const confirm = useCallback(
    (opts) =>
      new Promise((resolve) => {
        enqueue({
          kind: "confirm",
          variant: "default",
          ...opts,
          dialogInstanceId: nextDialogInstanceId(),
          resolve,
        });
      }),
    [enqueue],
  );

  const prompt = useCallback(
    (opts) =>
      new Promise((resolve) => {
        enqueue({
          kind: "prompt",
          ...opts,
          dialogInstanceId: nextDialogInstanceId(),
          resolve,
        });
      }),
    [enqueue],
  );

  const showToast = useCallback((message, opts) => {
    setToast({
      open: true,
      message: String(message || ""),
      severity: opts?.severity === "success" || opts?.severity === "error" ? opts.severity : "info",
    });
  }, []);

  const onToastClose = useCallback((_event, reason) => {
    if (reason === "clickaway") return;
    setToast((prev) => ({ ...prev, open: false }));
  }, []);

  const api = useMemo(() => ({ confirm, prompt, showToast }), [confirm, prompt, showToast]);

  return (
    <FeedbackContext.Provider value={api}>
      {children}
      <FeedbackDialogStack dialog={dialog} onResolve={resolveAndAdvance} />
      <Snackbar
        open={toast.open}
        onClose={onToastClose}
        autoHideDuration={2600}
        message={toast.message}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        slotProps={{
          content: {
            sx: {
              backgroundColor: "rgba(26,26,26,0.96)",
              border: "1px solid rgba(255,255,255,0.08)",
              color: "rgba(255,255,255,0.88)",
              fontSize: "0.8125rem",
            },
          },
        }}
      />
    </FeedbackContext.Provider>
  );
}
