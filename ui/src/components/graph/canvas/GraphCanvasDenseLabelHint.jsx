import React from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";

/**
 * Session-dismissible hint when "all" labels may overload dense graphs.
 *
 * @param {{
 *   message: string,
 *   switchAdaptiveLabel: string,
 *   switchInteractionLabel: string,
 *   onDismiss: () => void,
 *   onSwitchAdaptive: () => void,
 *   onSwitchInteraction: () => void,
 * }} props
 */
export default function GraphCanvasDenseLabelHint({
  message,
  switchAdaptiveLabel,
  switchInteractionLabel,
  onDismiss,
  onSwitchAdaptive,
  onSwitchInteraction,
}) {
  return (
    <Alert
      severity="info"
      variant="outlined"
      onClose={onDismiss}
      sx={{ flexShrink: 0, my: 0.5, fontSize: "0.75rem", py: 0.25 }}
    >
      {message}{" "}
      <Button size="small" sx={{ ml: 0.5, minWidth: 0 }} onClick={onSwitchAdaptive}>
        {switchAdaptiveLabel}
      </Button>
      <Button size="small" sx={{ ml: 0.5, minWidth: 0 }} onClick={onSwitchInteraction}>
        {switchInteractionLabel}
      </Button>
    </Alert>
  );
}
