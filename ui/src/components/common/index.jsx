import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";

const baseButtonSx = {
  textTransform: "none",
  fontWeight: 500,
  fontSize: "0.8125rem",
  borderRadius: 6,
  transition: "all 0.15s ease",
  border: "1px solid rgba(255, 255, 255, 0.12)",
  background: "rgba(255, 255, 255, 0.02)",
  color: "rgba(255, 255, 255, 0.9)",
  "&:hover": {
    background: "rgba(255, 255, 255, 0.06)",
    borderColor: "rgba(255, 255, 255, 0.18)",
  },
  "&:active": {
    transform: "scale(0.98)",
  },
};

export function CursorButton({ sx, ...props }) {
  return (
    <Button
      variant="outlined"
      sx={{ ...baseButtonSx, ...(sx || {}) }}
      {...props}
    />
  );
}

export function CursorPrimaryButton({ sx, ...props }) {
  return (
    <Button
      variant="outlined"
      sx={{
        ...baseButtonSx,
        background: "rgba(99, 102, 241, 0.15)",
        borderColor: "rgba(99, 102, 241, 0.3)",
        color: "rgba(129, 140, 248, 0.95)",
        "&:hover": {
          background: "rgba(99, 102, 241, 0.2)",
          borderColor: "rgba(99, 102, 241, 0.42)",
        },
        ...(sx || {}),
      }}
      {...props}
    />
  );
}

export function CursorDangerButton({ sx, ...props }) {
  return (
    <Button
      variant="outlined"
      sx={{
        ...baseButtonSx,
        color: "rgba(239, 68, 68, 0.8)",
        borderColor: "rgba(239, 68, 68, 0.2)",
        background: "transparent",
        "&:hover": {
          background: "rgba(239, 68, 68, 0.08)",
          borderColor: "rgba(239, 68, 68, 0.28)",
        },
        ...(sx || {}),
      }}
      {...props}
    />
  );
}

export function CursorIconButton({ sx, children, ...props }) {
  return (
    <IconButton
      size="small"
      sx={{
        padding: "6px",
        borderRadius: 6,
        border: "1px solid rgba(255, 255, 255, 0.12)",
        color: "rgba(255, 255, 255, 0.6)",
        transition: "all 0.15s ease",
        "&:hover": {
          background: "rgba(255, 255, 255, 0.06)",
          color: "rgba(255, 255, 255, 0.9)",
        },
        "&:active": {
          transform: "scale(0.98)",
        },
        ...(sx || {}),
      }}
      {...props}
    >
      {children}
    </IconButton>
  );
}

export function CursorSmallButton({ children, sx, ...props }) {
  return (
    <Button
      variant="outlined"
      sx={{
        ...baseButtonSx,
        fontSize: "0.75rem",
        padding: "4px 10px",
        minHeight: 28,
        ...(sx || {}),
      }}
      {...props}
    >
      <Typography component="span" sx={{ fontSize: "inherit" }}>
        {children}
      </Typography>
    </Button>
  );
}

