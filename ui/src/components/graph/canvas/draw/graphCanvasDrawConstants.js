/**
 * Shared canvas draw geometry and label-adaptive thresholds (no React).
 */

export const LABEL_FONT =
  '600 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif';
export const EDGE_LABEL_FONT =
  '400 10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif';
export const NODE_RADIUS = 12;
export const NODE_HIT_RADIUS = 18;
export const ARROW_HEAD_LEN = 7;
export const ARROW_HEAD_HW = 4;
export const EDGE_HOVER_THRESHOLD_PX = 8;
export const NODE_LABEL_HIT_PADDING_X = 10;
export const NODE_LABEL_HIT_PADDING_Y = 8;

/**
 * When edge count exceeds this or scale is below {@link EDGE_LABEL_ADAPTIVE_MIN_SCALE},
 * adaptive mode shows edge labels only for hover/selected edges. Values are tunable.
 */
export const EDGE_LABEL_ADAPTIVE_MAX_EDGES = 72;

/**
 * Above this edge count, adaptive mode behaves like "interaction" for mid-edge labels (paint cost).
 */
export const EDGE_LABEL_MEGA_DENSE_MIN_EDGES = 4000;

/** Below this screen scale (1 = 1px per world unit before pan), adaptive mode treats the view as zoomed out. */
export const EDGE_LABEL_ADAPTIVE_MIN_SCALE = 0.32;

/** When node count exceeds this or scale is below {@link NODE_LABEL_ADAPTIVE_MIN_SCALE}, community-mode node labels are gated. */
export const NODE_LABEL_ADAPTIVE_MAX_NODES = 48;

/** Below this scale, community-mode hides most node labels (selected/hovered/search hits still show). */
export const NODE_LABEL_ADAPTIVE_MIN_SCALE = 0.36;
