import { useEffect, useLayoutEffect, useMemo, useRef } from "react";

import { useGraphPhysicsPolicy } from "./useGraphPhysicsPolicy.js";
import {
  BOUNDS_SMOOTHING,
  createWorldBoundsCalculator,
  lerp,
} from "./scienceGraphSimulationBounds.js";
import { HIGH_REPULSION_STRENGTH_THRESHOLD } from "./scienceGraphSimulationTune.js";
import { getScienceDesiredDistance } from "../../components/graph/canvas/physics/desiredLinkDistance.js";
import { getNodeCluster } from "../../components/graph/canvas/physics/structuralCommunities.js";
import { detectScienceHybridCommunities } from "../../components/graph/canvas/physics/scienceHybridCommunities.js";
import {
  buildClusterPositionStats,
  centroidCommunityForce,
} from "../../components/graph/canvas/physics/communityCentroidAttraction.js";
import {
  BARNES_HUT_THETA,
  CANVAS_MARGIN,
  CLUSTER_ATTRACTION_STRENGTH,
  COMMUNITY_DETECTION_MAX_LINKS,
  COMMUNITY_DETECTION_MAX_NODES,
  COOLING_DECAY_RATE,
  COOLING_INITIAL_TEMPERATURE,
  COOLING_MIN_TEMPERATURE,
  COOLING_UPDATE_INTERVAL,
  MAX_VELOCITY,
  MAX_VELOCITY_SCALED,
  PHYSICS_REACT_COMMIT_INTERVAL,
  STABLE_ITERATIONS,
  STABILITY_THRESHOLD,
  USE_COMMUNITY_DETECTION,
} from "../../components/graph/canvas/physics/simConstants.js";
import { QuadTree } from "../../components/graph/canvas/physics/quadTree.js";
import { fastInvSqrt, fastSqrt, getRepulsionMultiplier } from "../../components/graph/canvas/physics/forceUtils.js";

/**
 * Force-directed simulation (fork of osint-gr useForceSimulation; no OSINT domain).
 *
 * @param {boolean} enabled
 * @param {import("../../components/graph/model/graphSimulationAdapter.js").SimNode[]} nodes
 * @param {React.Dispatch<React.SetStateAction<import("../../components/graph/model/graphSimulationAdapter.js").SimNode[]>>} setNodes
 * @param {import("../../components/graph/model/graphSimulationAdapter.js").SimLink[]} links
 * @param {number} repulsionStrength
 * @param {boolean} isSimulationStable
 * @param {(v: boolean) => void} setIsSimulationStable
 * @param {React.MutableRefObject<Set<string>>} fixedNodesRef
 * @param {React.MutableRefObject<{ id: string, x: number, y: number } | null>} draggedNodePositionRef
 * @param {{ width: number, height: number }} canvasSize
 * @param {string} topologySignature Canonical topology key (recompute communities when this changes).
 * @param {string} physicsEpoch Force-run / reheat identity; bumps reset cooling without redoing community detection if topology unchanged.
 * @param {string} simulationSignature Combined key for pause policy (`topology|physicsEpoch`); must change whenever topology or physicsEpoch changes.
 * @param {EventTarget} [pointerEventTarget] Optional bus for canvas pointer pause events (defaults to `window` via useGraphPhysicsPolicy).
 * @param {React.MutableRefObject<import("../../components/graph/model/graphSimulationAdapter.js").SimNode[]>} simNodesRef Live sim buffer (mutated in place); must match seeded React state after topology/restart.
 * @param {() => void} onPhysicsVisualTick Called after each integrator commit so canvas can repaint without setState per frame.
 */
export function useScienceGraphForceSimulation(
  enabled,
  nodes,
  setNodes,
  links,
  repulsionStrength,
  isSimulationStable,
  setIsSimulationStable,
  fixedNodesRef,
  draggedNodePositionRef,
  canvasSize,
  topologySignature,
  physicsEpoch,
  simulationSignature,
  pointerEventTarget,
  simNodesRef,
  onPhysicsVisualTick,
) {
  const animationRef = useRef(null);
  const boundsRef = useRef(null);
  const coolingTemperatureRef = useRef(COOLING_INITIAL_TEMPERATURE);
  const iterationCountRef = useRef(0);
  const communitiesRef = useRef(null);
  const prevTopologySigRef = useRef("");
  const prevPhysicsEpochRef = useRef("");
  /** Latest stable flag for the physics integrator (avoids stale closure while RAF runs). */
  const isSimStableRef = useRef(isSimulationStable);
  isSimStableRef.current = isSimulationStable;
  const prevRepulsionRef = useRef(repulsionStrength);
  const onPhysicsVisualTickRef = useRef(() => {});

  useLayoutEffect(() => {
    onPhysicsVisualTickRef.current = onPhysicsVisualTick;
  }, [onPhysicsVisualTick]);

  const calculateWorldBounds = useMemo(
    () => createWorldBoundsCalculator(canvasSize),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only width/height affect bounds math; object identity may churn per parent render
    [canvasSize.width, canvasSize.height],
  );

  const { integrationBlocked } = useGraphPhysicsPolicy({
    enabled,
    simulationSignature,
    animationFrameRef: animationRef,
    pointerEventTarget,
  });

  useEffect(() => {
    if (!enabled || integrationBlocked || nodes.length === 0) {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
      return undefined;
    }

    if (prevRepulsionRef.current !== repulsionStrength) {
      prevRepulsionRef.current = repulsionStrength;
      coolingTemperatureRef.current = COOLING_INITIAL_TEMPERATURE;
      iterationCountRef.current = 0;
      isSimStableRef.current = false;
      setIsSimulationStable(false);
    }

    if (prevTopologySigRef.current !== topologySignature) {
      prevTopologySigRef.current = topologySignature;
      prevPhysicsEpochRef.current = physicsEpoch;
      boundsRef.current = null;
      coolingTemperatureRef.current = COOLING_INITIAL_TEMPERATURE;
      iterationCountRef.current = 0;
      isSimStableRef.current = false;
      setIsSimulationStable(false);
      const communityEligible =
        USE_COMMUNITY_DETECTION &&
        nodes.length > 5 &&
        nodes.length <= COMMUNITY_DETECTION_MAX_NODES &&
        links.length <= COMMUNITY_DETECTION_MAX_LINKS;
      if (communityEligible) {
        communitiesRef.current = detectScienceHybridCommunities(nodes, links);
      } else {
        communitiesRef.current = null;
      }
    } else if (prevPhysicsEpochRef.current !== physicsEpoch) {
      prevPhysicsEpochRef.current = physicsEpoch;
      coolingTemperatureRef.current = COOLING_INITIAL_TEMPERATURE;
      iterationCountRef.current = 0;
      isSimStableRef.current = false;
      setIsSimulationStable(false);
    }

    const stableCountRef = { current: 0 };

    if (!boundsRef.current) {
      boundsRef.current = calculateWorldBounds(nodes);
    }

    const nodeTypeMap = new Map(nodes.map((n) => [n.id, n.type]));

    const linkMap = new Map();
    links.forEach((link) => {
      if (!linkMap.has(link.source)) linkMap.set(link.source, []);
      if (!linkMap.has(link.target)) linkMap.set(link.target, []);
      linkMap.get(link.source).push({ target: link.target, type: link.type });
      linkMap.get(link.target).push({ target: link.source, type: link.type });
    });

    const communityMap = new Map();
    if (communitiesRef.current) {
      communitiesRef.current.forEach((communityId, nodeId) => {
        if (!communityMap.has(communityId)) {
          communityMap.set(communityId, []);
        }
        communityMap.get(communityId).push(nodeId);
      });
      communityMap.forEach((ids) => {
        ids.sort((a, b) => String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" }));
      });
    }

    const nodeMap = new Map();

    /**
     * One integrator step mutating `newNodes` in place.
     * @returns {boolean} true if layout reached stable halt this step
     */
    const runOnePhysicsTick = (newNodes) => {
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
        const isHighRepulsion = repulsionStrength > HIGH_REPULSION_STRENGTH_THRESHOLD;

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

          let targetX = draggedPos && draggedPos.id === target.id ? draggedPos.x : target.x;
          let targetY = draggedPos && draggedPos.id === target.id ? draggedPos.y : target.y;
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

    const commitInterval = Math.max(1, Math.floor(PHYSICS_REACT_COMMIT_INTERVAL));

    const simulate = () => {
      const buf = simNodesRef.current;
      if (!buf || buf.length === 0) {
        animationRef.current = null;
        return;
      }

      let stableHalt = false;
      for (let s = 0; s < commitInterval; s++) {
        stableHalt = runOnePhysicsTick(buf);
        if (stableHalt) break;
      }

      onPhysicsVisualTickRef.current?.();

      if (stableHalt) {
        setNodes(buf.map((n) => ({ ...n })));
      }

      if (!stableHalt && (stableCountRef.current < STABLE_ITERATIONS || draggedNodePositionRef.current)) {
        animationRef.current = requestAnimationFrame(simulate);
      }
    };

    animationRef.current = requestAnimationFrame(simulate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- simulation uses simNodesRef; full `nodes` would restart every frame; `simulationSignature` is only for useGraphPhysicsPolicy above
  }, [
    enabled,
    integrationBlocked,
    simulationSignature,
    topologySignature,
    physicsEpoch,
    pointerEventTarget,
    links,
    repulsionStrength,
    isSimulationStable,
    canvasSize.width,
    canvasSize.height,
    calculateWorldBounds,
    setNodes,
    setIsSimulationStable,
    fixedNodesRef,
    draggedNodePositionRef,
    nodes.length,
    simNodesRef,
  ]);
}
