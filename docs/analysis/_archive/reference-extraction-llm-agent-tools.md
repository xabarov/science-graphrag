# Analysis: LLM agent with tools for reference extraction

**Scope:** This note covers the research spike in `scripts/experiment_references_smolagents_spike.py` (H2: `ToolCallingAgent` from **smolagents**). It also briefly contrasts the separate H1 path (`scripts/experiment_references_tool_router.py` + `science_graphrag/ingestion/llm/reference_tool_router.py`), which is **not** a multi-step tool agent.

**Date:** 2026-04-08

---

## 1. Agent prompt, goal, and task

### 1.1 Custom instructions (`instructions=`)

Injected into the smolagents tool-calling system template as `custom_instructions` (see `smolagents/prompts/toolcalling_agent.yaml`).

**Text in this repo:**

> You only have in-memory article tools. Goal: estimate how many bibliography references exist. Prefer calling heuristic_references once; use grep_article or get_lines only if you must verify where the references section starts.

**Stated goal:** estimate the **number** of bibliography references (counting / estimation), not full structured extraction of every citation.

### 1.2 User task (`agent.run(task)`)

> How many references does this article's bibliography contain? Give a single integer final answer after using tools.

### 1.3 Default smolagents layer

The full system prompt is built from `toolcalling_agent.yaml`: generic “expert assistant”, Action/Observation loop, `final_answer` requirement, tool list from `to_tool_calling_prompt()`, then the custom block above, then global rules (always provide a tool call, no duplicate identical calls, etc.).

---

## 2. Python code interpreter and allowed imports

### 2.1 In this spike: interpreter is **disabled**

The agent is constructed with `add_base_tools=False`, so **no** smolagents base tools are attached (no `python_interpreter`, no web search, no `visit_webpage`). Only the three custom tools below plus the built-in `final_answer` tool are available.

**Implication:** there is **no** project-specific whitelist of imports for a code interpreter in this script—the interpreter path is simply not used.

### 2.2 If `add_base_tools=True` on `ToolCallingAgent` (smolagents default behavior)

smolagents would add `PythonInterpreterTool` (and DuckDuckGo / VisitWebpage). For `PythonInterpreterTool`, allowed imports default to **`BASE_BUILTIN_MODULES`** from `smolagents/utils.py`:

- `collections`, `datetime`, `itertools`, `math`, `queue`, `random`, **`re`**, `stat`, `statistics`, `time`, `unicodedata`

The tool’s input description is updated to list these modules. Custom extra modules can be passed via `PythonInterpreterTool(..., authorized_imports=[...])` when instantiating the tool (not done in the spike).

---

## 3. Tools: names, descriptions, and code snippets

All definitions live in `scripts/experiment_references_smolagents_spike.py`.

### 3.1 `heuristic_references`

```python
class HeuristicRefsTool(Tool):
    name = "heuristic_references"
    description = (
        "Run the project's extract_references() on the full loaded article markdown. "
        "Returns JSON: count, first 5 raw_reference snippets, dois."
    )
    inputs: dict = {}
    output_type = "string"

    def __init__(self, text: str) -> None:
        super().__init__()
        self._text = text

    def forward(self) -> str:
        refs = extract_references(self._text)
        sample = [
            {
                "raw_reference": (r.raw_reference or "")[:200],
                "doi": r.doi,
                "arxiv_id": r.arxiv_id,
            }
            for r in refs[:5]
        ]
        return json.dumps({"count": len(refs), "sample": sample}, ensure_ascii=False)
```

### 3.2 `grep_article` (regex over lines)

```python
class GrepArticleTool(Tool):
    name = "grep_article"
    description = (
        "Search the loaded article with a Python regex; returns up to 30 lines "
        "(line number: text)."
    )
    inputs = {
        "pattern": {
            "type": "string",
            "description": "Python re pattern (e.g. References|\\\\[1\\\\])",
        },
    }
    output_type = "string"

    def __init__(self, text: str) -> None:
        super().__init__()
        self._text = text

    def forward(self, pattern: str) -> str:
        try:
            rx = re.compile(pattern)
        except re.error as e:
            return f"invalid_regex: {e}"
        out: list[str] = []
        for i, line in enumerate(self._text.splitlines(), start=1):
            if rx.search(line):
                out.append(f"{i}: {line[:500]}")
            if len(out) >= 30:
                break
        return "\n".join(out) if out else "(no matches)"
```

### 3.3 `get_lines`

```python
class GetLinesTool(Tool):
    name = "get_lines"
    description = "Return a 1-based inclusive slice of lines from the loaded article."
    inputs = {
        "start_line": {
            "type": "integer",
            "description": "First line number (1-based)",
        },
        "end_line": {
            "type": "integer",
            "description": "Last line number inclusive",
        },
    }
    output_type = "string"

    def __init__(self, text: str) -> None:
        super().__init__()
        self._text = text

    def forward(self, start_line: int, end_line: int) -> str:
        lines = self._text.splitlines()
        s = max(0, int(start_line) - 1)
        e = min(len(lines), int(end_line))
        chunk = "\n".join(lines[s:e])
        return chunk[:60_000] if chunk else "(empty)"
```

---

## 4. Regex ergonomics for the agent

**Without** `python_interpreter`, the model does **not** run arbitrary Python; it passes a **string pattern** into `grep_article`, which compiles it with `re.compile`.

**Pros:**

- Invalid patterns return `invalid_regex: ...` instead of crashing the run.
- Line-oriented output with numbers is easy to chain with `get_lines`.

**Cons:**

- The model must escape backslashes correctly in JSON/tool arguments (doubling is easy to get wrong; the example in the schema uses heavy escaping).
- Only **per-line** `search` is used: patterns cannot span lines unless the pattern is written to match within a single line; no `re.MULTILINE` / `DOTALL` flags are exposed.
- Stops after **30** matching lines—enough for “find References heading”, weak for “list every `[n]` marker” on long bibliographies.
- Truncates each hit to **500** characters.

So: **moderately** convenient for locating a section or a few markers; **poor** for complex multi-line bibliography parsing compared to a dedicated parser or flag-aware grep.

---

## 5. Is there a “grep” tool?

**Yes:** `grep_article` is a dedicated grep-like tool (regex, line-bounded, capped results).

**If you wanted something closer to Unix `grep`:**

| Need | Possible implementation |
|------|-------------------------|
| Fixed string vs regex | Add `fixed_string: bool` or separate `fgrep_article` using `re.escape` when true. |
| Case insensitivity | Add `flags` argument or `case_insensitive: bool` → `re.compile(..., re.I)`. |
| Multiline | Optional `multiline: bool` → pass `re.MULTILINE` / `re.DOTALL`, or run `rx.finditer` on the full text with chunking. |
| More than 30 hits | Raise limit, paginate (`offset`, `limit`), or return counts only. |
| Context lines | Add `-A/-B/-C` style context in the output builder. |
| Byte/encoding | Usually N/A for in-memory UTF-8 markdown already loaded. |

No extra dependency is strictly required; extend `GrepArticleTool.forward` (and `inputs`) and keep timeouts/size caps for safety.

---

## 6. Related path: H1 is not the same pattern

`reference_tool_router.extract_references_from_bibliography_excerpt` wraps an excerpt as synthetic `## References` and calls the same heuristic `extract_references` as full-document ingestion. The experiment script combines that with a **single** structured LLM call for scope (`ReferenceBibliographyScopeLLM`). There is **no** tool loop there—useful for production-shaped pipelines, but out of scope for “agent with tools” behavior.

---

## 7. Observed disadvantages and risks

1. **Narrow product goal:** The spike optimizes for a **count** after one heuristic call, not for extracting or validating each reference entry—misaligned if the real goal is bibliography **quality** or **completeness**.

2. **Cost and latency:** Each step is an LLM round-trip; compared to deterministic `extract_references` alone, this adds API cost without guaranteed accuracy gain for counting.

3. **No interpreter in use:** The model cannot run small scripts to reconcile ambiguous cases; enabling `python_interpreter` would widen capability but also **security and sandbox** concerns (even with smolagents’ restricted imports).

4. **Heuristic lock-in:** `heuristic_references` bakes in the project’s current regex/heuristic behavior; the agent mainly re-asks the same pipeline and may rationalize its count rather than discover new citations.

5. **Tool caps:** 30 lines / 500 chars / 60k chunk limit can hide evidence the model needs for edge cases (multi-section appendices, footnotes, inline refs).

6. **Maintenance:** Tool definitions are inline in a script, not shared with production ingestion—drift between “experiment agent” and shipped stages is likely.

7. **Evaluation gap:** The spike compares `final_answer` to `heuristic_baseline_count` in code comments intent only; robust eval would need parsing the integer answer and systematic benchmarks.

---

## 8. File reference

| Artifact | Role |
|----------|------|
| `scripts/experiment_references_smolagents_spike.py` | H2 `ToolCallingAgent` + custom tools |
| `scripts/experiment_references_tool_router.py` | H1 scope LLM + `extract_references_from_bibliography_excerpt` |
| `science_graphrag/ingestion/llm/reference_tool_router.py` | Deterministic excerpt → heuristic stage |
| `smolagents` (optional dep, `pyproject.toml` `[research]`) | Agent runtime |
