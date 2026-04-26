import React from "react";
import { Navigate, useLocation } from "react-router-dom";

import { CHAT_PATH } from "../routes/paths.js";

/** Preserves query string when migrating bookmarks from `/ask` to `/chat`. */
export default function LegacyAskRedirect() {
  const location = useLocation();
  return <Navigate to={{ pathname: CHAT_PATH, search: location.search }} replace />;
}
