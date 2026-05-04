## Learned User Preferences

- Iterates on SciGraph UI (graph workspace and Ask/chat flows) using screenshots and expects critique grounded in concrete `ui/` components and layout, not only generic advice.
- Often asks to merge scattered UX suggestions into one consolidated implementation plan, then wants that plan executed end-to-end without editing the plan file itself.
- After substantial UI work, may request a quality pass on the touched area: confirm completeness and fix remaining gaps or polish issues.
- Cares about toolbar and panel density; flags regressions such as extra vertical chrome, large empty regions next to controls, or redundant header chrome when navigation already signals context (e.g., obsolete page-title rows or legacy header actions on the Graph tab).
- For Habr-facing or other public export markdown, avoids internal repository paths (e.g., `eval/results/...`) that read as repo plumbing to external readers.
- When adding a consolidated analysis plan under `docs/analysis/`, retires superseded or duplicate analysis docs instead of leaving parallel versions.

## Learned Workspace Facts

- `WorkspaceGraphToolbar` uses separate labeled zones (filter vs panels) when `dense` is false, which stacks controls across more rows than the compact `dense` toolbar layout.
- On wide viewports the graph toolbar can show a large horizontal gap between left-side filters/search and right-aligned summary statistics, partly due to alignment and capped search field width.
- Graph canvas maintenance splits responsibilities across modules under `ui/src/components/graph/canvas/` (e.g., label-mode hooks, storage helpers, empty state) to keep `GraphCanvasMvp` within an enforced size budget.
