import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";
import { CssBaseline } from "@mui/material";

import Box from "@mui/material/Box";

import App from "./App.jsx";
import { FeedbackProvider } from "./components/feedback/index.js";
import { I18nProvider } from "./i18n/I18nContext.jsx";
import { AppearanceProvider } from "./theme/AppearanceProvider.jsx";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <I18nProvider>
      <AppearanceProvider>
        <FeedbackProvider>
          <CssBaseline />
          <HashRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <Box sx={{ flex: 1, minHeight: 0, height: "100%", display: "flex", flexDirection: "column" }}>
              <App />
            </Box>
          </HashRouter>
        </FeedbackProvider>
      </AppearanceProvider>
    </I18nProvider>
  </React.StrictMode>,
);

