import { useEffect, useLayoutEffect, useMemo, useRef } from "react";

import {
  COOLING_INITIAL_TEMPERATURE,
  PHYSICS_REACT_COMMIT_INTERVAL,
  STABLE_ITERATIONS,
} from "../../components/graph/canvas/physics/simConstants.js";
import { useGraphPhysicsPolicy } from "./useGraphPhysicsPolicy.js";
import { createWorldBoundsCalculator } from "./scienceGraphSimulationBounds.js";
import { buildSimulationGraphPrep } from "./scienceGraphSimulationGraphPrep.js";
import { applySimulationLifecycleResets } from "./scienceGraphSimulationResetPolicy.js";
import { createRunOnePhysicsTick } from "./scienceGraphSimulationTickEngine.js";

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
  const communitiesRef = useRef(/** @type {Map<string, string> | null} */ (null));
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

    applySimulationLifecycleResets({
      prevRepulsionRef,
      repulsionStrength,
      prevTopologySigRef,
      topologySignature,
      prevPhysicsEpochRef,
      physicsEpoch,
      boundsRef,
      coolingTemperatureRef,
      iterationCountRef,
      isSimStableRef,
      setIsSimulationStable,
      communitiesRef,
      nodes,
      links,
    });

    const stableCountRef = { current: 0 };

    if (!boundsRef.current) {
      boundsRef.current = calculateWorldBounds(nodes);
    }

    const { nodeTypeMap, linkMap, communityMap } = buildSimulationGraphPrep(
      nodes,
      links,
      communitiesRef.current,
    );

    const runOnePhysicsTick = createRunOnePhysicsTick({
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
    });

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
