import { describe, expect, it } from "vitest";

import { COOLING_INITIAL_TEMPERATURE } from "../../components/graph/canvas/physics/simConstants.js";
import { createWorldBoundsCalculator } from "./scienceGraphSimulationBounds.js";
import { buildSimulationGraphPrep } from "./scienceGraphSimulationGraphPrep.js";
import { createRunOnePhysicsTick } from "./scienceGraphSimulationTickEngine.js";

describe("createRunOnePhysicsTick", () => {
  it("pins dragged node coordinates and zeroes velocity", () => {
    const canvasSize = { width: 800, height: 600 };
    const calculateWorldBounds = createWorldBoundsCalculator(canvasSize);
    const boundsRef = { current: null };
    const coolingTemperatureRef = { current: COOLING_INITIAL_TEMPERATURE };
    const iterationCountRef = { current: 0 };
    const communitiesRef = { current: null };
    const fixedNodesRef = { current: new Set() };
    const draggedNodePositionRef = { current: { id: "a", x: 42, y: 99 } };
    const isSimStableRef = { current: false };
    const stableCountRef = { current: 0 };
    const setIsSimulationStable = () => {};

    const nodes = [
      { id: "a", x: 0, y: 0, vx: 10, vy: -5, type: "Work" },
      { id: "b", x: 200, y: 0, vx: 0, vy: 0, type: "Work" },
    ];
    const links = [];
    const { nodeTypeMap, linkMap, communityMap } = buildSimulationGraphPrep(nodes, links, null);

    const tick = createRunOnePhysicsTick({
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
      repulsionStrength: 0.5,
      isSimStableRef,
      setIsSimulationStable,
      stableCountRef,
    });

    const buf = nodes.map((n) => ({ ...n }));
    const halted = tick(buf);
    expect(halted).toBe(false);
    const a = buf.find((n) => n.id === "a");
    expect(a.x).toBe(42);
    expect(a.y).toBe(99);
    expect(a.vx).toBe(0);
    expect(a.vy).toBe(0);
  });

  it("zeroes velocity on fixed nodes with fx/fy", () => {
    const canvasSize = { width: 800, height: 600 };
    const calculateWorldBounds = createWorldBoundsCalculator(canvasSize);
    const boundsRef = { current: null };
    const coolingTemperatureRef = { current: COOLING_INITIAL_TEMPERATURE };
    const iterationCountRef = { current: 0 };
    const communitiesRef = { current: null };
    const fixedNodesRef = { current: new Set(["a"]) };
    const draggedNodePositionRef = { current: null };
    const isSimStableRef = { current: false };
    const stableCountRef = { current: 0 };
    const setIsSimulationStable = () => {};

    const nodes = [
      { id: "a", x: 50, y: 50, vx: 100, vy: 100, fx: 50, fy: 50, type: "Work" },
      { id: "b", x: 300, y: 50, vx: 0, vy: 0, type: "Work" },
    ];
    const links = [];
    const { nodeTypeMap, linkMap, communityMap } = buildSimulationGraphPrep(nodes, links, null);

    const tick = createRunOnePhysicsTick({
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
      repulsionStrength: 0.5,
      isSimStableRef,
      setIsSimulationStable,
      stableCountRef,
    });

    const buf = nodes.map((n) => ({ ...n }));
    tick(buf);
    const a = buf.find((n) => n.id === "a");
    expect(a.x).toBe(50);
    expect(a.y).toBe(50);
    expect(a.vx).toBe(0);
    expect(a.vy).toBe(0);
  });
});
