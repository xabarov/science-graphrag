/**
 * Force simulation tuning (ported subset from osint-gr graphVisualization/constants.js).
 */

export const STABILITY_THRESHOLD = 0.08;
export const STABLE_ITERATIONS = 60;
export const MAX_VELOCITY = 10;
export const MAX_VELOCITY_SCALED = 30;
export const CANVAS_MARGIN = 50;

export const COOLING_INITIAL_TEMPERATURE = 1.0;
export const COOLING_MIN_TEMPERATURE = 0.1;
export const COOLING_DECAY_RATE = 0.95;
export const COOLING_UPDATE_INTERVAL = 10;

export const USE_COMMUNITY_DETECTION = true;
export const CLUSTER_ATTRACTION_STRENGTH = 0.0003;

export const REPULSION_MIN = 2000;
export const REPULSION_MAX = 50000;
export const REPULSION_DEFAULT_PERCENT = 25;

/** @param {number} percent 0–100 */
export function percentToRepulsion(percent) {
  return REPULSION_MIN + (percent / 100) * (REPULSION_MAX - REPULSION_MIN);
}

/** @param {number} repulsion */
export function repulsionToPercent(repulsion) {
  return ((repulsion - REPULSION_MIN) / (REPULSION_MAX - REPULSION_MIN)) * 100;
}
