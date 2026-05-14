import {
  buildClusterPositionStats,
  centroidCommunityForce,
} from "../../components/graph/canvas/physics/communityCentroidAttraction.js";
import { getScienceDesiredDistance } from "../../components/graph/canvas/physics/desiredLinkDistance.js";
import { fastInvSqrt, fastSqrt, getRepulsionMultiplier } from "../../components/graph/canvas/physics/forceUtils.js";
import { QuadTree } from "../../components/graph/canvas/physics/quadTree.js";
import {
  BARNES_HUT_THETA,
  CANVAS_MARGIN,
  CLUSTER_ATTRACTION_STRENGTH,
  COOLING_DECAY_RATE,
  COOLING_MIN_TEMPERATURE,
  COOLING_UPDATE_INTERVAL,
  MAX_VELOCITY,
  MAX_VELOCITY_SCALED,
  STABLE_ITERATIONS,
  STABILITY_THRESHOLD,
} from "../../components/graph/canvas/physics/simConstants.js";
import { getNodeCluster } from "../../components/graph/canvas/physics/structuralCommunities.js";
import {
  BOUNDS_SMOOTHING,
  lerp,
} from "./scienceGraphSimulationBounds.js";
import { HIGH_REPULSION_STRENGTH_THRESHOLD } from "./scienceGraphSimulationTune.js";

/**
 * Factory for one integrator step (mutates node array in place).
 *
 * @param {{
 *   calculateWorldBounds: (nodes: import("../../components/graph/model/graphSimulationAdapter.js").SimNode[]) => {
 *     minX: number,
 *     maxX: number,
 *     minY: number,
 *     maxY: number,
 *     width: number,
 *     height: number,
 *   },
 *   boundsRef: React.MutableRefObject<unknown>,
 *   coolingTemperatureRef: React.MutableRefObject<number>,
 *   iterationCountRef: React.MutableRefObject<number>,
 *   communitiesRef: React.MutableRefObject<Map<string, string> | null>,
 *   communityMap: Map<string, string[]>,
 *   nodeTypeMap: Map<string, string | undefined>,
 *   linkMap: Map<string, Array<{ target: string, type?: string }>>,
 *   fixedNodesRef: React.MutableRefObject<Set<string>>,
 *   draggedNodePositionRef: React.MutableRefObject<{ id: string, x: number, y: number } | null>,
 *   repulsionStrength: number,
 *   isSimStableRef: React.MutableRefObject<boolean>,
 *   setIsSimulationStable: (v: boolean) => void,
 *   stableCountRef: { current: number },
 * }} deps
 * @returns {(newNodes: import("../../components/graph/model/graphSimulationAdapter.js").SimNode[]) => boolean} true when stable halt this step
 */
export function createRunOnePhysicsTick(deps) {
  const {
    calculateWorldBounds,
    boundsRef,
    coolingTemperatureRef,
    iterationCountRef,
    communitiesRef,
    communityMap,
    nodeTypeMap,
    linkMap,
    fixedNodesRef,
    draggedNodePositionRef,
    repulsionStrength,
    isSimStableRef,
    setIsSimulationStable,
    stableCountRef,
  } = deps;

  const nodeMap = new Map();

  return function runOnePhysicsTick(newNodes) {
    let totalVelocity = 0;
    let activeNodes = 0;

    const draggedPos = draggedNodePositionRef.current;

    const targetBounds = calculateWorldBounds(newNodes);
    const prevBounds = boundsRef.current ?? targetBounds;
    const effectiveBounds = {
      minX: lerp(prevBounds.minX, targetBounds.minX, BOUNDS_SMOOTHING),
      minY: lerp(prevBounds.minY, targetBounds.minY, BOUNDS_SMOOTHING),
      maxX: lerp(prevBounds.maxX, targetBounds.maxX, BOUNDS_SMOOTHING),
      maxY: lerp(prevBounds.maxY, targetBounds.maxY, BOUNDS_SMOOTHING),
    };
    effectiveBounds.width = effectiveBounds.maxX - effectiveBounds.minX;
    effectiveBounds.height = effectiveBounds.maxY - effectiveBounds.minY;
    boundsRef.current = effectiveBounds;

    nodeMap.clear();
    newNodes.forEach((node) => {
      nodeMap.set(node.id, node);
    });

    /** @type {Map<unknown, { sumX: number, sumY: number, count: number, draggedMemberId: string | null }> | null} */
    let clusterStats = null;
    if (communitiesRef.current && communityMap.size > 0) {
      clusterStats = buildClusterPositionStats(communityMap, nodeMap, draggedPos);
    }

    let quadtree = null;
    if (newNodes.length > 10) {
      const margin = 100;
      quadtree = new QuadTree({
        x: effectiveBounds.minX - margin,
        y: effectiveBounds.minY - margin,
        width: effectiveBounds.width + 2 * margin,
        height: effectiveBounds.height + 2 * margin,
      });

      newNodes.forEach((node) => {
        if (draggedPos && draggedPos.id === node.id) return;
        quadtree.insert({ x: node.x, y: node.y, id: node.id });
      });
    }

    const isHighRepulsion = repulsionStrength > HIGH_REPULSION_STRENGTH_THRESHOLD;

    newNodes.forEach((node) => {
      if (draggedPos && draggedPos.id === node.id) {
        node.x = draggedPos.x;
        node.y = draggedPos.y;
        node.vx = 0;
        node.vy = 0;
        return;
      }

      if (fixedNodesRef.current.has(node.id)) {
        if (node.fx !== undefined && node.fy !== undefined) {
          node.x = node.fx;
          node.y = node.fy;
        }
        node.vx = 0;
        node.vy = 0;
        return;
      }

      let fx = 0;
      let fy = 0;
      const nodeType = nodeTypeMap.get(node.id);

      if (quadtree && newNodes.length > 10) {
        const repulsion = quadtree.calculateRepulsion(
          node.x,
          node.y,
          node.id,
          nodeType,
          undefined,
          nodeTypeMap,
          repulsionStrength,
          draggedPos,
          BARNES_HUT_THETA,
        );
        fx += repulsion.fx;
        fy += repulsion.fy;
      } else {
        newNodes.forEach((other) => {
          if (node.id === other.id) return;

          let otherX = other.x;
          let otherY = other.y;
          if (draggedPos && draggedPos.id === other.id) {
            otherX = draggedPos.x;
            otherY = draggedPos.y;
          }

          const dx = node.x - otherX;
          const dy = node.y - otherY;
          const distSq = dx * dx + dy * dy + 1;
          const invDist = fastInvSqrt(distSq);

          const otherType = nodeTypeMap.get(other.id);
          const repulsionMultiplier = getRepulsionMultiplier(nodeType, otherType, undefined, undefined);

          const forceScale = repulsionStrength > HIGH_REPULSION_STRENGTH_THRESHOLD ? 1.5 : 1.0;
          const force = repulsionStrength * repulsionMultiplier * forceScale * invDist * invDist;
          fx += dx * invDist * force;
          fy += dy * invDist * force;
        });
      }

      const nodeLinks = linkMap.get(node.id) || [];
      nodeLinks.forEach((linkData) => {
        const target = nodeMap.get(linkData.target);
        if (!target) return;

        const targetX = draggedPos && draggedPos.id === target.id ? draggedPos.x : target.x;
        const targetY = draggedPos && draggedPos.id === target.id ? draggedPos.y : target.y;
        const dx = targetX - node.x;
        const dy = targetY - node.y;
        const distSq = dx * dx + dy * dy;

        if (distSq > 0) {
          const dist = fastSqrt(distSq);
          const desiredDist = getScienceDesiredDistance(linkData.type);

          let stiffness = 0.015;
          if (isHighRepulsion) {
            stiffness *= 0.5;
          }

          const force = (dist - desiredDist) * stiffness;
          const invDist = 1 / dist;
          fx += dx * invDist * force;
          fy += dy * invDist * force;
        }
      });

      if (clusterStats && communitiesRef.current) {
        const nodeCluster = getNodeCluster(node.id, communitiesRef.current);
        if (nodeCluster) {
          const c = centroidCommunityForce(
            node.id,
            nodeCluster,
            clusterStats,
            { x: node.x, y: node.y },
            draggedPos,
            CLUSTER_ATTRACTION_STRENGTH,
            coolingTemperatureRef.current,
            fastSqrt,
          );
          fx += c.fx;
          fy += c.fy;
        }
      }

      const coolingFactor = coolingTemperatureRef.current;

      const stable = isSimStableRef.current;
      const baseDamping = stable && draggedPos ? 0.65 : stable ? 0.55 : 0.8;
      const baseVelocityMultiplier = stable && draggedPos ? 0.25 : stable ? 0.35 : 0.6;

      const dampingFactor = isHighRepulsion ? Math.max(0.7, baseDamping) : baseDamping;
      let velocityMultiplier = isHighRepulsion ? Math.min(1.0, baseVelocityMultiplier * 1.5) : baseVelocityMultiplier;

      velocityMultiplier *= coolingFactor;

      node.vx = (node.vx + fx * velocityMultiplier) * dampingFactor;
      node.vy = (node.vy + fy * velocityMultiplier) * dampingFactor;

      const maxVel = isHighRepulsion ? MAX_VELOCITY_SCALED : MAX_VELOCITY;
      const velocitySq = node.vx * node.vx + node.vy * node.vy;
      let velocity = 0;
      if (velocitySq > maxVel * maxVel) {
        velocity = fastSqrt(velocitySq);
        node.vx = (node.vx / velocity) * maxVel;
        node.vy = (node.vy / velocity) * maxVel;
        velocity = maxVel;
      } else {
        velocity = fastSqrt(velocitySq);
      }

      if (!draggedPos) {
        totalVelocity += velocity;
        activeNodes += 1;
      }

      node.x += node.vx;
      node.y += node.vy;

      const minX = effectiveBounds.minX + CANVAS_MARGIN;
      const maxX = effectiveBounds.maxX - CANVAS_MARGIN;
      const minY = effectiveBounds.minY + CANVAS_MARGIN;
      const maxY = effectiveBounds.maxY - CANVAS_MARGIN;

      if (node.x < minX) {
        node.x = minX;
        node.vx *= -0.2;
      } else if (node.x > maxX) {
        node.x = maxX;
        node.vx *= -0.2;
      }
      if (node.y < minY) {
        node.y = minY;
        node.vy *= -0.2;
      } else if (node.y > maxY) {
        node.y = maxY;
        node.vy *= -0.2;
      }
    });

    iterationCountRef.current += 1;
    if (iterationCountRef.current % COOLING_UPDATE_INTERVAL === 0) {
      if (coolingTemperatureRef.current > COOLING_MIN_TEMPERATURE) {
        coolingTemperatureRef.current = Math.max(
          COOLING_MIN_TEMPERATURE,
          coolingTemperatureRef.current * COOLING_DECAY_RATE,
        );
      }
    }

    if (!draggedPos) {
      const avgVelocity = activeNodes > 0 ? totalVelocity / activeNodes : 0;
      const effectiveThreshold = STABILITY_THRESHOLD * (1 + (1 - coolingTemperatureRef.current) * 0.5);

      if (avgVelocity < effectiveThreshold) {
        stableCountRef.current += 1;
        if (stableCountRef.current >= STABLE_ITERATIONS) {
          newNodes.forEach((node) => {
            node.vx = 0;
            node.vy = 0;
          });
          if (!isSimStableRef.current) {
            isSimStableRef.current = true;
            setIsSimulationStable(true);
          }
          return true;
        }
      } else {
        stableCountRef.current = 0;
      }
    }

    return false;
  };
}
