/**
 * Canvas draw pipeline: thin facade re-exporting draw phases and hit tests.
 * Implementation lives under `./draw/`.
 */

export {
  ARROW_HEAD_HW,
  ARROW_HEAD_LEN,
  EDGE_HOVER_THRESHOLD_PX,
  EDGE_LABEL_ADAPTIVE_MAX_EDGES,
  EDGE_LABEL_ADAPTIVE_MIN_SCALE,
  EDGE_LABEL_FONT,
  EDGE_LABEL_MEGA_DENSE_MIN_EDGES,
  LABEL_FONT,
  NODE_HIT_RADIUS,
  NODE_LABEL_ADAPTIVE_MAX_NODES,
  NODE_LABEL_ADAPTIVE_MIN_SCALE,
  NODE_LABEL_HIT_PADDING_X,
  NODE_LABEL_HIT_PADDING_Y,
  NODE_RADIUS,
} from "./draw/graphCanvasDrawConstants.js";
export { strokeAtHalfAlpha } from "./draw/graphCanvasDrawColor.js";
export { shouldDrawCanvasEdgeLabel, shouldDrawCanvasNodeLabel } from "./draw/graphCanvasDrawLabelPolicy.js";
export { drawEdges } from "./draw/graphCanvasDrawEdges.js";
export { drawNodes } from "./draw/graphCanvasDrawNodes.js";
export { drawLabels } from "./draw/graphCanvasDrawLabels.js";
export { hitTestClosestEdgeId, hitTestNode, hitTestNodeScreen } from "./draw/graphCanvasDrawHitTest.js";
