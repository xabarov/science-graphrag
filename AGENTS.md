## Learned User Preferences

- Iterates on SciGraph UI (graph workspace and Ask/chat flows) using screenshots and expects critique grounded in concrete `ui/` components and layout, not only generic advice.
- Often asks to merge scattered UX suggestions into one consolidated implementation plan, then wants that plan executed end-to-end without editing the plan file itself.
- After substantial UI work, may request a quality pass on the touched area: confirm completeness and fix remaining gaps or polish issues.
- Cares about toolbar and panel density; flags regressions such as extra vertical chrome or large empty regions next to controls when layouts change.

## Learned Workspace Facts

- `WorkspaceGraphToolbar` uses separate labeled zones (filter vs panels) when `dense` is false, which stacks controls across more rows than the compact `dense` toolbar layout.
- On wide viewports the graph toolbar can show a large horizontal gap between left-side filters/search and right-aligned summary statistics, partly due to alignment and capped search field width.
- Graph canvas maintenance splits responsibilities across modules under `ui/src/components/graph/canvas/` (e.g., label-mode hooks, storage helpers, empty state) to keep `GraphCanvasMvp` within an enforced size budget.
