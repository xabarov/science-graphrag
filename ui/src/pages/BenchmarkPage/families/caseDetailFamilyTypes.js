/**
 * @typedef {import("react").ReactNode} ReactNode
 */

/**
 * Context passed to optional family-specific UI in the case detail dialog.
 * @typedef {object} CaseDetailFamilyExtrasContext
 * @property {unknown} [detail]
 * @property {unknown} [artifacts]
 * @property {string | null} caseId
 * @property {string} family
 * @property {(to: string) => void} navigate
 * @property {() => void} [onClose]
 */

/**
 * @callback RenderCaseDetailExtras
 * @param {CaseDetailFamilyExtrasContext} ctx
 * @returns {ReactNode}
 */

/**
 * Per-benchmark-family UI/config for CaseDetailDialog.
 * @typedef {object} CaseDetailFamilyConfig
 * @property {boolean} usesLayer1Gold
 * @property {"layer1" | "graph" | null} graphSnapshotApiFamily API family for postGraphSnapshotPreview; null when not applicable.
 * @property {RenderCaseDetailExtras | undefined} [renderCaseDetailExtras]
 */

export {};
