/**
 * Report-first benchmark experiment catalog (Phase 0).
 * Maps user-facing experiments to launcher/API surfaces and metric semantics.
 *
 * Implementation is split under `./catalog/`; this module re-exports the stable surface.
 */

export * from "./catalog/experimentCatalogData.js";
export * from "./catalog/experimentCatalogTabs.js";
export * from "./catalog/experimentCatalogRunLab.js";
