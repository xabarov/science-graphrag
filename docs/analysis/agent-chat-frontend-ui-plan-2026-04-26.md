# Agent chat frontend UI/UX implementation plan — 2026-04-26

**Status:** draft  
**Scope:** `ui/` chat experience for agent turns, stream progress, subagent visibility, typed result blocks  
**Primary context:** `docs/analysis/chat-agent-system-roadmap-2026-04-26.md`, `docs/specs/agent-chat-v1.md`

## 1. Why this plan exists

The current research chat already has a usable foundation:

- `ChatMessageThread.jsx` gives us a clean threaded surface and scroll behavior.
- `AskAnswerPanel.jsx` already renders typed payloads and lightweight stream lines.
- `ChatTypedBlocks.jsx` already separates structured results such as inventory, quotes, and bibliography.
- `useAgentStream.js` already exposes an SSE event stream suitable for richer live UI.

What is still missing is a **product-quality agent chat surface** that makes long-running turns legible and trustworthy:

- the user should immediately see that the system is doing work, not just "thinking";
- subagent activity should be visible without flooding the thread;
- intermediate progress should be compact by default and expandable on demand;
- the final answer should feel like the result of a traceable run, not a plain text blob;
- the loading state should feel polished and modern, with a silver shimmer instead of a generic spinner.

## 2. UX goals

### 2.1 Primary goals

1. Make every assistant turn feel like a **run with stages**, not a black box.
2. Show **subagent activity and safe reasoning summaries** without exposing raw chain-of-thought.
3. Keep the default view **compact and calm**, with deeper inspection one click away.
4. Preserve focus on the **final answer and evidence**, not on diagnostics for their own sake.
5. Reuse the existing dark Cursor-like visual system already present in `ui/`.

### 2.2 Non-goals

1. Do not turn the chat into a developer console.
2. Do not expose raw prompts, hidden rationale, or verbose tool payloads inline by default.
3. Do not create a second, separate event UI outside the message thread unless later usability testing proves it is necessary.

## 3. Design references to reuse

### 3.1 From `science-graphrag`

- Keep the existing thread layout, spacing, chips, and border rhythm from `ChatMessageThread.jsx`.
- Keep typed answer sections from `ChatTypedBlocks.jsx`, but make them visually subordinate to the final answer card.
- Keep stream parsing in `useAgentStream.js`; do not reinvent the transport model.

### 3.2 From `osint-gr`

Two patterns are especially worth adapting:

1. `frontend/src/components/common/ShimmerText.jsx`
   - silver animated gradient;
   - lightweight and readable;
   - better emotional quality than a default `CircularProgress`.

2. `frontend/src/components/features/CompactChat/components/InvestigationSessionMessage.jsx`
   - collapsible event tree;
   - compact status lines with expandable detail;
   - visually separate "process" from "final answer".

The goal is **not** to clone the OSINT UI literally. The goal is to adapt its strongest ideas into the research-workspace chat.

## 4. Product-safe visibility model

The user asked for visibility into "what the subagent is thinking". In the product, this should mean:

- high-level progress summaries;
- selected route or specialist;
- what class of work is happening now;
- what evidence has already been gathered;
- whether the system compacted memory or hit a warning.

It should **not** mean raw hidden reasoning text.

### 4.1 Approved visible summary formats

Visible stream summaries should be phrased as short operational statements, for example:

- "Classified as grounded explanation"
- "Routing to retrieval specialist"
- "Searching paper chunks for supporting evidence"
- "Collected 4 candidate quotes"
- "Compact memory updated for this thread"

### 4.2 Subagent mental model in UI

For the user, each subagent should be shown as a **work block** with:

- name;
- current state;
- one-line summary;
- optional event count or evidence count;
- expandable log.

This creates transparency without leaking hidden prompts or raw internal traces.

## 5. Proposed message anatomy

Each assistant turn should render as a stacked composition rather than one flat panel.

### 5.1 Turn header strip

At the top of each live or completed assistant turn:

- assistant label, optionally with answer class chip;
- run state chip: `Running`, `Done`, `Warning`, `Degraded`, `Failed`;
- optional duration and evidence count on completed runs;
- subtle trace affordance for future OTel/Phoenix drill-down.

Visual style:

- slim header row;
- muted text;
- small chips;
- no heavy backgrounds.

### 5.2 Live activity strip

When streaming is active, render a compact live strip directly under the header:

- silver shimmer text;
- last meaningful status summary;
- animated pulse dot or moving divider;
- optional "N events" meta label.

Example behavior:

- default state: one line only;
- hover or expand: show recent event list;
- when the first substantive event arrives, replace "Thinking..." with the real status.

### 5.3 Subagent block rail

If the run includes route changes, specialist selection, or future explicit subagent events, show a vertical stack of subagent cards:

- compact default height;
- one card per specialist/subagent run;
- clear state colors only through restrained opacity, not bright badges;
- expandable body with recent events and evidence counters.

Each card should support two levels:

1. **Compact mode**
   - name;
   - short status;
   - current step;
   - one chevron.

2. **Expanded mode**
   - event timeline;
   - tools used;
   - warnings;
   - evidence summary;
   - completion status.

### 5.4 Final answer card

The final answer remains the most important block:

- stronger typography than the live status rail;
- evidence summary directly beneath the answer intro;
- typed blocks below the prose answer;
- citations below typed blocks;
- tool trace moved into a lower-priority "Inspect run" section.

### 5.5 Inspection drawer inside the message

For power users, each assistant turn should have a collapsed "Inspect run" area:

- raw tool trace;
- full event list;
- structured warnings;
- compact/session events;
- future `phoenix_trace_id`.

This keeps the primary UI clean while preserving observability.

## 6. Visual language

The chat should stay aligned with the existing dark UI rules:

- background layers: `#0a0a0a`, `#141414`, `#1a1a1a`;
- borders: thin, low-contrast;
- radius: `6px`;
- typography: compact, dense, neutral;
- interaction: soft transitions, no heavy shadows.

### 6.1 Silver shimmer spec

For active thinking states, use a silver gradient close to the successful OSINT reference:

- base tone: `rgba(192, 192, 200, 0.40)`
- highlight tone: `rgba(220, 220, 230, 0.82)`
- trailing tone: `rgba(192, 192, 200, 0.40)`
- animation duration: `2.4s` to `2.8s`
- animation style: smooth horizontal shimmer, never flashing

Recommended usage:

- loading line label;
- active subagent title when running;
- "assembling answer" status;
- never on large paragraphs of body text.

### 6.2 Block hierarchy

Use three visual tiers:

1. **Primary**
   - final answer body;
   - user message bubble.

2. **Secondary**
   - subagent cards;
   - typed blocks;
   - citations.

3. **Tertiary**
   - raw trace;
   - low-level event details;
   - debug metadata.

This is critical; otherwise the stream UI will overpower the answer.

### 6.3 Shared live-progress language for ingest

The same silver shimmer language should also be used for **workspace ingest**, not only for agent chat.

Today the ingest surface in `WorkspaceContextStrip.jsx` is visually reduced to a thin blue progress bar. That communicates "something is busy", but it does **not** communicate:

- what phase the ingest is currently in;
- whether the current phase is binary or has real sub-progress;
- how much of the total path is still left;
- why the bar may appear "stuck" during a long LLM or embedding step.

The goal is to make ingest feel like a **traceable run with phases**, similar to agent chat, while keeping the compact workspace strip calm and low-noise.

#### 6.3.1 Recommended compact ingest strip

Replace the current ultra-thin bar with a compact status block approximately `220px` to `280px` wide.

Recommended anatomy:

1. **Primary live line**
   - silver shimmer text;
   - current high-level phase label;
   - right-aligned overall percentage.

2. **Secondary detail line**
   - current raw stage label or short humanized summary;
   - optional sub-progress such as `31 / 82 chunks`.

3. **Thin segmented bar**
   - phase-weighted overall progress;
   - subdued separators between major phases;
   - no bright colors beyond the existing muted accent.

Example compact states:

- `Preparing document` · `18%`
- `Building knowledge graph` · `47%`
- `Preparing search layer` · `78%`
- `Finalizing` · `96%`

Secondary examples:

- `Extracting metadata and references`
- `Resolving references · 18 / 24`
- `Embedding chunks · 31 / 82`

#### 6.3.2 Two-level ingest mental model

The ingest pipeline already has many domain stages. The UI should not expose all of them equally at the compact level.

Use two levels:

1. **Product phase** for the compact strip
2. **Raw stage** for the expanded details card

Recommended product phases:

1. `Preparing document`
   - `parse_pdf`
   - `extract_meta`

2. `Building knowledge graph`
   - `enrich_openalex`
   - `enrich_ror`
   - `write_graph`
   - `resolve_references`

3. `Preparing search layer`
   - `chunk`
   - `extract_claims`
   - `embed`

4. `Finalizing`
   - `attach_workspace`

This gives users a stable, understandable mental model while still allowing engineering-grade details one click deeper.

#### 6.3.3 Stage-by-stage progress semantics

Not every stage should expose a fake percentage. The UI should distinguish between:

1. **Binary stages**
   - best represented as `queued / running / completed / failed`;
   - examples: `enrich_openalex`, `enrich_ror`, `attach_workspace`.

2. **Step-based stages**
   - better represented through named substeps rather than arbitrary percentages;
   - examples: `extract_meta`, `write_graph`, `chunk`.

3. **True measurable stages**
   - should expose real counters when available;
   - examples:
     - `parse_pdf` via `processed_pages / total_pages`
     - `resolve_references` via `linked / total`
     - `extract_claims` via `processed_chunks / total_chunks` or batch counts
     - `embed` via `embedded_items / total_items`

This distinction is important. A beautiful but dishonest progress indicator will reduce trust.

#### 6.3.4 Relative time cost across the full path

The backend already computes ingest progress using **historical expected stage duration**, not just number of completed stages. That is the correct direction and should remain the canonical source for the overall percentage.

However, the current weighted-progress behavior treats every running stage as a flat **half-complete stage**. This explains why the blue bar can feel static during a long step and then jump abruptly near the end.

Recommended interpretation for UX:

1. Keep the current weighted overall progress as the fallback.
2. Upgrade the running-stage contribution from fixed `0.5 * stage_weight` to:
   - `stage_weight * active_fraction`
3. Only show sub-progress where `active_fraction` is grounded in real counters.

Approximate relative cost profile to design around:

1. **Low-cost stages**
   - `enrich_openalex`
   - `enrich_ror`
   - `attach_workspace`

2. **Medium-cost stages**
   - `parse_pdf` for simple text inputs
   - `resolve_references`
   - `chunk`

3. **High-cost stages**
   - `extract_meta`
   - `write_graph`
   - `extract_claims`
   - `embed`

The UI should therefore visually emphasize progress *within* the high-cost stages, because that is where users currently perceive "nothing is happening".

#### 6.3.5 Expanded ingest details card

When the user opens the ingest popover or progress card, show:

1. current product phase;
2. current raw stage;
3. overall weighted percentage;
4. stage list with completed/running/failed states;
5. stage metrics in humanized form;
6. logs and warnings below the structured view.

Each raw stage row should support:

- human label;
- machine stage id in secondary text only if useful;
- status chip or symbol;
- optional elapsed / expected time;
- optional metrics summary.

Examples of good metrics copy:

- `Processed 6 / 14 PDF pages`
- `Found 24 references`
- `Linked 18 / 24 references`
- `Prepared 82 chunks`
- `Embedded 31 / 82 chunks`
- `Extracted 12 claims`

#### 6.3.6 Shimmer alignment between chat and ingest

The shimmer pattern should be shared between:

- agent chat live status;
- subagent active labels;
- ingest compact live strip;
- ingest running phase label.

It should *not* be used for:

- large answer paragraphs;
- completed states;
- long logs;
- multiple simultaneous lines in the same compact card.

This keeps a consistent product language: shimmer means **active trustworthy work is happening now**.

The existing `osint-gr` `ShimmerText.jsx` pattern is a good visual base and should be adapted rather than copied literally.

#### 6.3.7 Backend additions that would unlock a much better UI

The current ingest event stream already gives the frontend:

- `snapshot`
- `stage_started`
- `stage_finished`
- `stage_failed`
- `batch_progress`
- `terminal`

That is enough for a first improved card, but not enough for a truly honest live percentage inside long stages.

Recommended additions:

1. `stage_progress`
   - incremental updates while a stage is running;
   - payload should include `current`, `total`, `unit`, optional message, and metrics.

2. `active_fraction`
   - explicit `0..1` fraction for the current stage when measurable.

3. `phase`
   - canonical product phase name in the payload or derivable through a shared mapping.

4. `heartbeat_message`
   - short product-safe status line for long silent operations.

Example payload:

```json
{
  "job_id": "abc",
  "stage": "embed",
  "phase": "preparing_search_layer",
  "status": "running",
  "current": 31,
  "total": 82,
  "unit": "chunks",
  "active_fraction": 0.378,
  "message": "Embedding chunks",
  "metrics": {
    "embedded_chunks": 31,
    "total_chunks": 82
  }
}
```

#### 6.3.8 Recommended delivery order for ingest UX

This should be delivered in two waves:

1. **Ingest UI-1: frontend-only polish**
   - widen the compact ingest area;
   - replace the lone blue bar with shimmer + phase + percent;
   - humanize stage names and metrics;
   - keep current weighted percentage as the fallback.

2. **Ingest UI-2: truthful live sub-progress**
   - add `stage_progress`;
   - add measurable `active_fraction`;
   - compute weighted overall progress using real running-stage completion;
   - expose phase-aware counters in the expanded card.

This sequence gives an immediate product win without blocking on backend refactors, while still aiming for a genuinely trustworthy progress model.

## 7. Event-to-UI mapping

The current SSE vocabulary is already sufficient for a first strong UI pass.

### 7.1 Events that should affect live chrome immediately

- `intent_classified`
  - update run header with answer-class chip;
  - emit a short summary in the live activity strip.

- `specialist_selected`
  - open or update a subagent card;
  - mark the selected specialist as active.

- `tool_search_result`
  - append a compact summary to the active specialist card;
  - optionally show shortlisted tool count.

- `tool_call`
  - update active specialist step;
  - increment action count.

- `tool_result`
  - mark success or warning;
  - capture row count or error note.

- `evidence_ready`
  - update evidence chip;
  - move emphasis from "searching" to "assembling answer".

- `context_compacted`
  - add a small memory chip or status note;
  - log event in the inspection section.

- `warning`
  - show subdued warning state on the turn header;
  - keep full text inside expanded details.

- `final_answer`
  - freeze the run UI;
  - collapse live shimmer;
  - promote final answer block to primary state.

### 7.2 New events recommended for frontend excellence

The current event vocabulary works, but the UI would become much better with a small set of product-safe additions:

1. `subagent_started`
2. `subagent_progress`
3. `subagent_finished`
4. `answer_synthesis_started`
5. `answer_synthesis_finished`

Each should contain only compact summaries, status, and optional counters.

These are not mandatory for the first wave, but they would allow a much clearer subagent rail than inferring everything from `specialist_selected` and generic tool events.

## 8. Proposed component architecture

Keep the implementation incremental and close to the existing files.

### 8.1 Components to add

1. `ui/src/components/work/AgentRunHeader.jsx`
   - state chip, answer class, duration, evidence count.

2. `ui/src/components/work/AgentLiveStatus.jsx`
   - silver shimmer line;
   - compact recent status summary;
   - optional expand/collapse.

3. `ui/src/components/work/AgentSubagentRail.jsx`
   - renders specialist/subagent cards from stream events.

4. `ui/src/components/work/AgentSubagentCard.jsx`
   - compact/expanded block for one subagent run.

5. `ui/src/components/work/AgentEventTimeline.jsx`
   - nested or flat event renderer for expanded views.

6. `ui/src/components/work/ShimmerLabel.jsx`
   - local adaptation of the silver shimmer pattern.

7. `ui/src/components/work/AgentRunInspector.jsx`
   - raw trace, warnings, memory compaction notes, debug payloads.

### 8.2 Existing files to reshape

1. `ChatMessageThread.jsx`
   - replace the standalone spinner/text pending state with a real assistant turn shell.

2. `AskAnswerPanel.jsx`
   - split into clearer sections:
     - run chrome;
     - final answer;
     - typed blocks;
     - citations;
     - inspection area.

3. `ChatTypedBlocks.jsx`
   - unify card styling and spacing so typed blocks look like one family.

4. `useAgentStream.js`
   - keep transport behavior;
   - optionally add event normalization helpers upstream if the UI model grows.

5. `ui/src/services/agent/agentStreamParse.js`
   - extend normalization to compute a stable frontend event model for the subagent rail.

### 8.3 State shape recommended on the client

Introduce a derived run model separate from raw events:

- `runState`
- `answerClass`
- `activeSpecialist`
- `subagentRuns[]`
- `recentStatusLine`
- `evidenceCount`
- `warningCodes[]`
- `memoryCompacted`
- `inspector`

This prevents presentation logic from being scattered across multiple components.

## 9. Interaction details

### 9.1 Default collapsed behavior

On a normal completed assistant turn, the user should see:

- the final answer;
- one-line run summary;
- at most one visible compact subagent row if it adds meaning;
- typed blocks if present;
- citations.

Everything else should start collapsed.

### 9.2 Expanded behavior

Expanding the run reveals:

- subagent cards;
- event timeline;
- warnings;
- traceability details.

Expanding a subagent reveals:

- recent steps;
- tools used;
- counts and warnings;
- completion result.

### 9.3 Streaming behavior

While the answer is still running:

- show the assistant turn shell immediately after the user message;
- use shimmer instead of a lone spinner;
- auto-scroll only while the user remains near the bottom;
- avoid large layout jumps when typed payloads appear at the end.

### 9.4 Mobile and narrow widths

For smaller widths:

- keep only one-line summaries visible by default;
- move chips into wrapping rows;
- keep inspector collapsed;
- avoid dual-column layouts inside a message.

## 10. Accessibility and trust

### 10.1 Accessibility

1. All expanders need clear `aria-label`s.
2. Shimmer must remain readable with reduced motion fallback.
3. Status changes should not rely on color alone.
4. Cards must stay keyboard navigable.

### 10.2 Trust heuristics

1. Prefer "Collected 4 quotes" over opaque "processing".
2. Show warnings near the answer, not only in hidden trace.
3. Make degraded answers visually distinct but not alarming.
4. Never imply certainty without evidence or counts.

## 11. Implementation phases

### UI-1. Turn shell and shimmer foundation

**Goal:** replace the primitive loading state with a polished agent turn shell.

Deliver:

- `ShimmerLabel.jsx`
- `AgentRunHeader.jsx`
- `AgentLiveStatus.jsx`
- updated pending state in `ChatMessageThread.jsx`

Acceptance:

- pending assistant turn appears immediately;
- silver shimmer replaces plain text/spinner-only feedback;
- no regressions in scroll behavior.

### UI-2. Structured run chrome inside `AskAnswerPanel`

**Goal:** separate live progress, final answer, typed blocks, and inspector.

Deliver:

- refactored `AskAnswerPanel.jsx`
- cleaner spacing hierarchy
- collapsed "Inspect run" section

Acceptance:

- final answer visually dominates;
- stream status is visible but compact;
- tool trace is no longer mixed into the main answer area.

### UI-3. Subagent rail

**Goal:** make routing and specialist work visible in a beautiful compact form.

Deliver:

- `AgentSubagentRail.jsx`
- `AgentSubagentCard.jsx`
- derived frontend model from stream events

Acceptance:

- user can tell which specialist was active;
- compact mode remains low-noise;
- expanded mode provides useful detail.

### UI-4. Typed block polish

**Goal:** make structured outputs feel like first-class answer sections.

Deliver:

- unified block chrome in `ChatTypedBlocks.jsx`
- better titles, spacing, and action affordances
- optional iconography only if it remains subtle

Acceptance:

- inventory, quotes, and bibliography look related but not identical;
- blocks feel integrated into the answer card.

### UI-5. Event vocabulary upgrade

**Goal:** improve frontend clarity with product-safe subagent events.

Deliver:

- optional backend event additions;
- parser and model updates;
- richer subagent progress summaries.

Acceptance:

- the UI no longer has to infer too much from generic tool calls;
- subagent states map directly to explicit event semantics.

## 12. Verification plan

### 12.1 Frontend checks

1. `agentStreamParse` tests for new event normalization.
2. Component tests for:
   - collapsed and expanded subagent cards;
   - shimmer live state;
   - warning/degraded state;
   - final answer with typed blocks.
3. manual SSE run against live backend to verify event ordering and perceived smoothness.

### 12.2 UX acceptance scenarios

1. Simple inventory answer finishes quickly and stays compact.
2. Quote search shows live search progress, then renders quotes cleanly.
3. Long multi-step run shows specialist changes without overwhelming the thread.
4. Warning case shows degraded trust indicators without breaking layout.
5. Follow-up turn with `context_compacted` shows memory activity subtly.

## 13. Open decisions

The following decisions should be made before UI-3:

1. Do we keep the subagent rail entirely inside each assistant message, or also mirror the active run in a sticky side panel?
2. Do we want explicit backend subagent events now, or do UI-3 using inferred specialist cards first?
3. Should citations remain below typed blocks, or move into a right-aligned expandable evidence drawer later?
4. Do we want a future "trace" icon linking to Phoenix when `phoenix_trace_id` is present?

## 14. Recommended immediate next step

Start with **UI-1 + UI-2 together**.

That gives the biggest visible product improvement with minimal backend dependency:

- polished live turn shell;
- silver shimmer;
- better hierarchy between process and final answer;
- cleaner foundation for later subagent cards.
