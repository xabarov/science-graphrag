import { createContext } from "react";

/**
 * @typedef {{
 *   confirm: (opts: {
 *     title: string,
 *     body?: string,
 *     confirmLabel?: string,
 *     cancelLabel?: string,
 *     variant?: "danger" | "default",
 *   }) => Promise<boolean>,
 *   prompt: (opts: {
 *     title: string,
 *     description?: string,
 *     label?: string,
 *     defaultValue?: string,
 *     confirmLabel?: string,
 *     cancelLabel?: string,
 *     validate?: (value: string) => string | null,
 *   }) => Promise<string | null>,
 *   showToast: (message: string, opts?: { severity?: "info" | "success" | "error" }) => void,
 * }} FeedbackApi
 */

/** @type {import("react").Context<FeedbackApi | null>} */
export const FeedbackContext = createContext(null);
