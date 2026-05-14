import { detectScienceHybridCommunities } from "../../components/graph/canvas/physics/scienceHybridCommunities.js";
import {
  COMMUNITY_DETECTION_MAX_LINKS,
  COMMUNITY_DETECTION_MAX_NODES,
  COOLING_INITIAL_TEMPERATURE,
  USE_COMMUNITY_DETECTION,
} from "../../components/graph/canvas/physics/simConstants.js";

/**
 * Repulsion / topology / physics-epoch lifecycle resets for the force integrator.
 * Mutates refs and may call setIsSimulationStable(false).
 *
 * @param {{
 *   prevRepulsionRef: React.MutableRefObject<number>,
 *   repulsionStrength: number,
 *   prevTopologySigRef: React.MutableRefObject<string>,
 *   topologySignature: string,
 *   prevPhysicsEpochRef: React.MutableRefObject<string>,
 *   physicsEpoch: string,
 *   boundsRef: React.MutableRefObject<unknown>,
 *   coolingTemperatureRef: React.MutableRefObject<number>,
 *   iterationCountRef: React.MutableRefObject<number>,
 *   isSimStableRef: React.MutableRefObject<boolean>,
 *   setIsSimulationStable: (v: boolean) => void,
 *   communitiesRef: React.MutableRefObject<Map<string, string> | null>,
 *   nodes: import("../../components/graph/model/graphSimulationAdapter.js").SimNode[],
 *   links: import("../../components/graph/model/graphSimulationAdapter.js").SimLink[],
 * }} p
 */
export function applySimulationLifecycleResets({
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
}) {
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
}
