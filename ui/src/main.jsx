import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";
import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";

import Box from "@mui/material/Box";

import App from "./App.jsx";
import { I18nProvider } from "./i18n/I18nContext.jsx";
import "./styles.css";

const theme = createTheme({
  palette: {
    mode: "dark",
    background: {
      default: "#0a0a0a",
    },
  },
  typography: {
    fontFamily: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontSize: 13,
  },
});

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <I18nProvider>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <HashRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Box sx={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
            <App />
          </Box>
        </HashRouter>
      </ThemeProvider>
    </I18nProvider>
  </React.StrictMode>,
);

