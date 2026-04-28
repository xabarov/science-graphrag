import { useEffect, useRef } from "react";

import { useGraphPhysicsPolicy } from "./useGraphPhysicsPolicy.js";
import { getScienceDesiredDistance } from "../../components/graph/physics/desiredLinkDistance.js";
import { getNodeCluster } from "../../components/graph/physics/structuralCommunities.js";
import { detectScienceHybridCommunities } from "../../components/graph/physics/scienceHybridCommunities.js";
import {
  CANVAS_MARGIN,
  CLUSTER_ATTRACTION_STRENGTH,
  COOLING_DECAY_RATE,
  COOLING_INITIAL_TEMPERATURE,
  COOLING_MIN_TEMPERATURE,
  COOLING_UPDATE_INTERVAL,
  MAX_VELOCITY,
  MAX_VELOCITY_SCALED,
  STABLE_ITERATIONS,
  STABILITY_THRESHOLD,
  USE_COMMUNITY_DETECTION,
} from "../../components/graph/physics/simConstants.js";
import { QuadTree } from "../../components/graph/physics/quadTree.js";
import { fastInvSqrt, fastSqrt, getRepulsionMultiplier } from "../../components/graph/physics/forceUtils.js";

/**
 * Force-directed simulation (fork of osint-gr useForceSimulation; no OSINT domain).
 *
 * @param {boolean} enabled
 * @param {import("../../components/graph/graphSimulationAdapter.js").SimNode[]} nodes
 * @param {React.Dispatch<React.SetStateAction<import("../../components/graph/graphSimulationAdapter.js").SimNode[]>>} setNodes
 * @param {import("../../components/graph/graphSimulationAdapter.js").SimLink[]} links
 * @param {number} repulsionStrength
 * @param {boolean} isSimulationStable
 * @param {(v: boolean) => void} setIsSimulationStable
 * @param {React.MutableRefObject<Set<string>>} fixedNodesRef
 * @param {React.MutableRefObject<{ id: string, x: number, y: number } | null>} draggedNodePositionRef
 * @param {{ width: number, height: number }} canvasSize
 * @param {string} simulationSignature topology + optional run id (restarts) so cooling/communities reset without graph change
 * @param {EventTarget} [pointerEventTarget] Optional bus for canvas pointer pause events (defaults to `window` via useGraphPhysicsPolicy).
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
  simulationSignature,
  pointerEventTarget,
) {
  const animationRef = useRef(null);
  const boundsRef = useRef(null);
  const coolingTemperatureRef = useRef(COOLING_INITIAL_TEMPERATURE);
  const iterationCountRef = useRef(0);
  const communitiesRef = useRef(null);
  const prevSimSigRef = useRef("");
  /** Latest stable flag for the physics integrator (avoids stale closure while RAF runs). */
  const isSimStableRef = useRef(isSimulationStable);
  isSimStableRef.current = isSimulationStable;
  const prevRepulsionRef = useRef(repulsionStrength);

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

    if (prevSimSigRef.current !== simulationSignature) {
      prevSimSigRef.current = simulationSignature;
      boundsRef.current = null;
      coolingTemperatureRef.current = COOLING_INITIAL_TEMPERATURE;
      iterationCountRef.current = 0;
      setIsSimulationStable(false);
      if (USE_COMMUNITY_DETECTION && nodes.length > 5) {
        communitiesRef.current = detectScienceHybridCommunities(nodes, links);
      } else {
        communitiesRef.current = null;
      }
    }

    const stableCountRef = { current: 0 };
    const WORLD_SCALE = 3;
    const MIN_WORLD_SPAN = Math.max(canvasSize.width, canvasSize.height) * WORLD_SCALE;
    const SMOOTHING = 0.15;
    const lerp = (a, b, t) => a + (b - a) * t;

    const calculateWorldBounds = (nodeList) => {
      if (!nodeList || nodeList.length === 0) {
        const halfSpan = MIN_WORLD_SPAN / 2 + CANVAS_MARGIN * 2;
        // World-space bounds must not use screen pixel centers (nodes live in world coords).
        return {
          minX: -halfSpan,
          maxX: halfSpan,
          minY: -halfSpan,
          maxY: halfSpan,
          width: halfSpan * 2,
          height: halfSpan * 2,
        };
      }

      let minX = Infinity;
      let maxX = -Infinity;
      let minY = Infinity;
      let maxY = -Infinity;

      nodeList.forEach((node) => {
        if (node.x < minX) minX = node.x;
        if (node.x > maxX) maxX = node.x;
        if (node.y < minY) minY = node.y;
        if (node.y > maxY) maxY = node.y;
      });

      const spanX = Math.max(maxX - minX, MIN_WORLD_SPAN);
      const spanY = Math.max(maxY - minY, MIN_WORLD_SPAN);
      const padding = Math.max(CANVAS_MARGIN * 2, Math.max(spanX, spanY) * 0.15);
      const centerX = (minX + maxX) / 2;
      const centerY = (minY + maxY) / 2;
      const halfX = spanX / 2 + padding;
      const halfY = spanY / 2 + padding;

      return {
        minX: centerX - halfX,
        maxX: centerX + halfX,
        minY: centerY - halfY,
        maxY: centerY + halfY,
        width: halfX * 2,
        height: halfY * 2,
      };
    };

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
    }

    const nodeMap = new Map();

    const simulate = () => {
      setNodes((prevNodes) => {
        const newNodes = prevNodes.map((node) => ({ ...node }));
        let totalVelocity = 0;
        let activeNodes = 0;

        const draggedPos = draggedNodePositionRef.current;

        const targetBounds = calculateWorldBounds(newNodes);
        const prevBounds = boundsRef.current;
        const effectiveBounds = {
          minX: lerp(prevBounds.minX, targetBounds.minX, SMOOTHING),
          minY: lerp(prevBounds.minY, targetBounds.minY, SMOOTHING),
          maxX: lerp(prevBounds.maxX, targetBounds.maxX, SMOOTHING),
          maxY: lerp(prevBounds.maxY, targetBounds.maxY, SMOOTHING),
        };
        effectiveBounds.width = effectiveBounds.maxX - effectiveBounds.minX;
        effectiveBounds.height = effectiveBounds.maxY - effectiveBounds.minY;
        boundsRef.current = effectiveBounds;

        nodeMap.clear();
        newNodes.forEach((node) => {
          nodeMap.set(node.id, node);
        });

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
          const isHighRepulsion = repulsionStrength > 20000;

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

              const forceScale = repulsionStrength > 20000 ? 1.5 : 1.0;
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

          if (communitiesRef.current && communityMap.size > 0) {
            const nodeCluster = getNodeCluster(node.id, communitiesRef.current);
            if (nodeCluster) {
              const clusterNodes = communityMap.get(nodeCluster) || [];
              clusterNodes.forEach((otherId) => {
                if (otherId === node.id) return;
                if (draggedPos && draggedPos.id === otherId) return;

                const other = nodeMap.get(otherId);
                if (!other) return;

                const dx = other.x - node.x;
                const dy = other.y - node.y;
                const distSq = dx * dx + dy * dy + 1;
                const dist = fastSqrt(distSq);

                const communityForce = dist * CLUSTER_ATTRACTION_STRENGTH * coolingTemperatureRef.current;
                const invDist = 1 / dist;
                fx += dx * invDist * communityForce;
                fy += dy * invDist * communityForce;
              });
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
              return newNodes;
            }
          } else {
            stableCountRef.current = 0;
          }
        }

        return newNodes;
      });

      if (stableCountRef.current < STABLE_ITERATIONS || draggedNodePositionRef.current) {
        animationRef.current = requestAnimationFrame(simulate);
      }
    };

    animationRef.current = requestAnimationFrame(simulate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- simulation uses setNodes(prev=>...); full `nodes` would restart every frame
  }, [
    enabled,
    integrationBlocked,
    simulationSignature,
    pointerEventTarget,
    links,
    repulsionStrength,
    isSimulationStable,
    canvasSize.width,
    canvasSize.height,
    setNodes,
    setIsSimulationStable,
    fixedNodesRef,
    draggedNodePositionRef,
    nodes.length,
  ]);
}
