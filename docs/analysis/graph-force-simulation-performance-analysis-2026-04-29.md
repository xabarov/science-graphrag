# Graph force simulation: performance ceiling, complexity, and acceleration paths

**Date:** 2026-04-29  
**Scope:** client-side force-directed layout in `ui/` (`useScienceGraphForceSimulation`, quadtree repulsion, link forces, community attraction, React integration).  
**Related:** [`refactor-frontend.md`](../backlog/refactor-frontend.md) (follow-ups if large refactors are scheduled).

---

## 1. Executive summary

The graph “physics engine” is **not** at a theoretical dead end. Repulsion already uses a **Barnes–Hut quadtree** for `n > 10`, which is typically **O(n log n)** per tick for many-body approximation. Remaining headroom includes:

1. **Algorithmic:** community-cluster attraction can degrade to **O(n²)** per tick when one cluster dominates all nodes.
2. **Integration:** each animation frame clones all nodes inside `setNodes`, forcing **O(n)** allocations plus React reconciliation—often the practical bottleneck before pure force math is exhausted.
3. **Ecosystem:** WebGPU / WASM / worker-based layouts and stronger LOD or pre-layout strategies are well-established options for large graphs.

This note records **asymptotic cost per tick**, **concrete code locations**, a **phased roadmap** (§4), and a flat **prioritized** list (§5) for cross-reference.

---

## 2. Current implementation (code map)

| Concern | Location |
|--------|----------|
| Simulation loop, cooling, stability, bounds | [`ui/src/hooks/graph/useScienceGraphForceSimulation.js`](../../ui/src/hooks/graph/useScienceGraphForceSimulation.js) |
| Barnes–Hut quadtree + `calculateRepulsion` | [`ui/src/components/graph/physics/quadTree.js`](../../ui/src/components/graph/physics/quadTree.js) |
| Constants (cooling, thresholds, community flag) | [`ui/src/components/graph/physics/simConstants.js`](../../ui/src/components/graph/physics/simConstants.js) |
| When integration runs (shell / canvas pause) | [`ui/src/hooks/graph/useGraphPhysicsPolicy.js`](../../ui/src/hooks/graph/useGraphPhysicsPolicy.js) |

Behavioral summary:

- **Repulsion:** brute-force **O(n²)** pairs when `n ≤ 10`; for larger `n`, rebuild a quadtree each tick and query Barnes–Hut with default `theta = 0.5`.
- **Links:** adjacency from `linkMap`; per-node neighbor iteration → **O(n + m)** per tick (`m` = undirected edge count in the map).
- **Community attraction:** for each node, iterate every other node in the same community id → worst-case **O(∑|C|²)** across communities (single giant cluster → **O(n²)**).

---

## 3. Per-tick asymptotic complexity

Let `n` = nodes, `m` = edges, clusters `C` with sizes `|C|`.

| Component | Typical | Worst / notes |
|-----------|---------|----------------|
| Quadtree build + `n` inserts | **O(n log n)** | Tree depth depends on spatial distribution |
| Barnes–Hut repulsion (all nodes) | **O(n log n)** | Larger `theta` → faster, coarser approximation |
| Brute-force repulsion | **O(n²)** | Only used for `n ≤ 10` |
| Link (spring) forces | **O(n + m)** | Linear in edges stored per endpoint |
| Community intra-cluster forces | **O(∑|C|²)** | **O(n²)** if one cluster contains most nodes |
| Node clone + `setNodes` | **O(n)** | Plus React render cost (not captured in Big-O of forces alone) |

**Dominant term in practice:** for dense UIs and large `n`, **React + rendering + labels** often dominates before Barnes–Hut is asymptotically “maxed out.”

---

## 4. Phased roadmap (quick wins → serious changes)

Stages are ordered by **typical effort vs risk**. Items in later stages may supersede or duplicate earlier ones (e.g. WebGPU can make some CPU micro-optimizations irrelevant). Use **Chrome Performance** after each stage to confirm the dominant cost moved as expected.

| Stage | Goal | Effort (order of magnitude) | Main levers |
|-------|------|-----------------------------|-------------|
| **A — Quick wins** ✅ *done (code)* | Cheaper ticks without structural rewrites | Hours to ~1 day | See **Stage A — delivery notes** below (θ constant + wiring; topology vs `physicsEpoch` warm start + canonical layout signature; `PHYSICS_REACT_COMMIT_INTERVAL` batching; default throttle = 1). *Manual Chrome Performance still recommended per §4.* |
| **B — High leverage, local code** | Remove worst asymptotics and main-thread React tax from the hot path | Days | **Community forces:** replace pairwise same-cluster loops with attraction to **cluster centroids** (or per-cluster spatial index) — removes quadratic-in-cluster-size cost (sum over communities of cluster-size squared). **React integration:** stop cloning all nodes every rAF — mutable sim buffer + **batched** or **position-only** state updates, or drive canvas from refs/imperative layer with minimal React reconciliation. |
| **C — Architecture** | Same physics model, better throughput and frame pacing | Weeks | **Web Worker** for force integration (transferables / shared buffers); **WASM** SoA hot loop (pairs well with worker). **Rendering:** edge/label LOD, decouple heavy paint from sim tick rate where the profile shows paint/layout bound. |
| **D — Ecosystem / product** | Very large graphs or new rendering stack | Weeks to months | **WebGPU** compute layout (e.g. GraphGPU, d3-force-webgpu, graphwagu); **multilevel / LOD** graph (simulate coarse graph, interpolate); **server-side or offline pre-layout** (ship `x,y` with payload, client refines). |

**Stage A — delivery notes (implemented in `ui/`, 2026-04-29):**

1. **Barnes–Hut `theta`** — `BARNES_HUT_THETA` in [`ui/src/components/graph/physics/simConstants.js`](../../ui/src/components/graph/physics/simConstants.js) (default `0.5`, same as legacy implicit default); passed into [`QuadTree.calculateRepulsion`](../../ui/src/components/graph/physics/quadTree.js) from [`useScienceGraphForceSimulation`](../../ui/src/hooks/graph/useScienceGraphForceSimulation.js). Raise toward ~0.65–0.75 only after profiling if repulsion is still hot.
2. **Warm start / fewer cold restarts** — [`GraphCanvasMvp.jsx`](../../ui/src/components/graph/GraphCanvasMvp.jsx) passes `topologySignature` and `physicsEpoch` separately; physics-only bumps reset cooling/stability **without** re-running `detectScienceHybridCommunities`. [`getGraphLayoutSignature`](../../ui/src/components/graph/graphFlowAdapter.js) uses **canonical sort** of node/edge ids so reorder-only API payloads do not retrigger topology reseed. Follow-ups: `isSimStableRef` sync on reset, `simulationSignature` in effect deps for policy alignment, deterministic cluster id lists (small quality pass).
3. **Throttle / batched commits** — `PHYSICS_REACT_COMMIT_INTERVAL` in `simConstants.js` (default **1** = one physics tick per React commit, unchanged UX). Values **2–4** run multiple `runOnePhysicsTick` substeps per `setNodes` to trade motion smoothness for fewer reconciles; validate per graph size.

**Suggested sequencing:** complete **A** before large refactors; run **B** community + React integration fixes in parallel only if staffed — both touch `useScienceGraphForceSimulation.js` and should land with tests/regression checks. **C** and **D** are optional forks depending on target `n` and UX (interactive drag vs static overview).

---

## 5. Acceleration paths (flat prioritized list)

Cross-check with §4; numbering here is priority within category, not strict timeline.

### 5.1 Low-risk, high leverage (same stack)

1. **Reduce React work per frame**  
   Avoid deep-cloning every node every `requestAnimationFrame` when only positions change; use mutable simulation state + throttled/partial updates, or batch commits (e.g. every 2–4 frames). This targets the **integration** cost, not the force model.

2. **Fix community-force scaling**  
   Replace pairwise same-cluster loops with forces toward **cluster centroids** (or a secondary spatial index per cluster). Removes **O(|C|²)** spikes.

3. **Tune Barnes–Hut `theta`**  
   Expose or adjust `theta` in `calculateRepulsion` (currently fixed default `0.5`). Higher → fewer tree visits → faster, less accurate repulsion.

4. **Warm start / fewer restarts**  
   Preserve positions across minor topology changes; avoid full cold restarts when `simulationSignature` changes unnecessarily.

### 5.2 Medium effort (architecture)

5. **Web Worker** for force integration  
   Moves CPU work off the main thread; still requires efficient transfer or shared buffers; does not alone reduce total CPU if the main thread still re-renders everything every frame.

6. **WASM hot loop**  
   SoA layout, SIMD-friendly math; pairs well with (5).

### 5.3 Higher effort (ecosystem)

7. **WebGPU compute**  
   Examples: [GraphGPU](https://github.com/drkameleon/GraphGPU) (CPU Barnes–Hut + optional GPU layout), [d3-force-webgpu](https://github.com/jamescarruthers/d3-force-webgpu), Rust/wgpu crates with Barnes–Hut + WebGPU (e.g. `vibe-graph-layout-gpu` on crates.io). GPU paths often use **O(n²)**-style work with massive parallelism; throughput can win for medium `n` even without hierarchical N-body on GPU.

8. **Graph simplification / LOD**  
   Simulate a coarsened graph or visible subgraph; interpolate or lazy-expand.

9. **Server-side or offline pre-layout**  
   Ship positions with the graph payload for large static views; client only refines.

**Mapping to §4:** items **3–4** → Stage **A**; **1–2** → Stage **B**; **5–6** (and rendering-focused slices of **8**) → Stage **C**; **7–9** → Stage **D**.

---

## 6. Answer to “have we exhausted headroom?”

**No.** Even with Barnes–Hut:

- Community attraction can still be **quadratic** in pathological (and sometimes realistic) clusterings.
- **Per-frame React cloning** is an avoidable **O(n)** tax on top of forces.
- **Rendering** (edges, labels, picking) can cap FPS independently of force asymptotics.

Profiling (Chrome Performance): attribute time among `simulate` / quadtree / `setNodes` / layout / paint before picking a single optimization theme.

---

## 7. Optional follow-ups (not committed here)

If a future session implements structural changes, consider logging a concrete backlog item under [`docs/backlog/refactor-frontend.md`](../backlog/refactor-frontend.md) with acceptance criteria (e.g. “no full node clone every rAF tick” or “community forces O(n) worst case”).

---

## 8. References (external)

- GraphGPU — WebGPU rendering + CPU Barnes–Hut / GPU layout: https://github.com/drkameleon/GraphGPU  
- d3-force-webgpu — GPU-accelerated d3-force style API: https://github.com/jamescarruthers/d3-force-webgpu  
- Barnes–Hut classic trade-off: `theta` controls accuracy vs speed (see GraphGPU README tables).
