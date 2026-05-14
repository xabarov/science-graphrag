import { describe, expect, it, vi } from "vitest";

import { COOLING_INITIAL_TEMPERATURE } from "../../components/graph/canvas/physics/simConstants.js";
import { applySimulationLifecycleResets } from "./scienceGraphSimulationResetPolicy.js";

describe("applySimulationLifecycleResets", () => {
  it("resets cooling when repulsion strength changes", () => {
    const prevRepulsionRef = { current: 1 };
    const coolingTemperatureRef = { current: 0.2 };
    const iterationCountRef = { current: 99 };
    const isSimStableRef = { current: true };
    const setIsSimulationStable = vi.fn();
    const boundsRef = { current: { minX: 0 } };
    const communitiesRef = { current: new Map([["a", "c"]]) };
    const prevTopologySigRef = { current: "topo-a" };
    const prevPhysicsEpochRef = { current: "e0" };

    applySimulationLifecycleResets({
      prevRepulsionRef,
      repulsionStrength: 2,
      prevTopologySigRef,
      topologySignature: "topo-a",
      prevPhysicsEpochRef,
      physicsEpoch: "e0",
      boundsRef,
      coolingTemperatureRef,
      iterationCountRef,
      isSimStableRef,
      setIsSimulationStable,
      communitiesRef,
      nodes: [{ id: "a" }],
      links: [],
    });

    expect(prevRepulsionRef.current).toBe(2);
    expect(coolingTemperatureRef.current).toBe(COOLING_INITIAL_TEMPERATURE);
    expect(iterationCountRef.current).toBe(0);
    expect(isSimStableRef.current).toBe(false);
    expect(setIsSimulationStable).toHaveBeenCalledWith(false);
    expect(boundsRef.current).toEqual({ minX: 0 });
  });

  it("clears bounds and recomputes communities when topology signature changes", () => {
    const prevRepulsionRef = { current: 5 };
    const coolingTemperatureRef = { current: 0.1 };
    const iterationCountRef = { current: 10 };
    const isSimStableRef = { current: true };
    const setIsSimulationStable = vi.fn();
    const boundsRef = { current: { minX: 1 } };
    const communitiesRef = { current: null };
    const prevTopologySigRef = { current: "old" };
    const prevPhysicsEpochRef = { current: "0|0" };

    const nodes = [
      { id: "a", type: "Work" },
      { id: "b", type: "Work" },
      { id: "c", type: "Work" },
      { id: "d", type: "Work" },
      { id: "e", type: "Work" },
      { id: "f", type: "Work" },
    ];
    const links = [{ source: "a", target: "b", type: "HAS_AUTHORSHIP" }];

    applySimulationLifecycleResets({
      prevRepulsionRef,
      repulsionStrength: 5,
      prevTopologySigRef,
      topologySignature: "new",
      prevPhysicsEpochRef,
      physicsEpoch: "1|0",
      boundsRef,
      coolingTemperatureRef,
      iterationCountRef,
      isSimStableRef,
      setIsSimulationStable,
      communitiesRef,
      nodes,
      links,
    });

    expect(prevTopologySigRef.current).toBe("new");
    expect(prevPhysicsEpochRef.current).toBe("1|0");
    expect(boundsRef.current).toBeNull();
    expect(communitiesRef.current).toBeInstanceOf(Map);
    expect(communitiesRef.current.size).toBeGreaterThan(0);
  });
});
