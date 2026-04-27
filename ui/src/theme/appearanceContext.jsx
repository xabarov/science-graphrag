import { createContext } from "react";

/** @typedef {{ preference: "dark"|"light"|"system", effective: "dark"|"light", setPreference: (v: "dark"|"light"|"system") => void }} AppearanceContextValue */

/** @type {import("react").Context<AppearanceContextValue | null>} */
export const AppearanceContext = createContext(null);
