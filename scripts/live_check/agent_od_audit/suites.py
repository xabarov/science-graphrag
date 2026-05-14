"""Question packs for OD workspace E2E audit."""

from __future__ import annotations

ACCEPTANCE_V3_QUESTIONS: list[tuple[str, str]] = [
    (
        "v3_cv_fanout_dual_evidence",
        (
            "Compare evidence for two different object-detection works in this workspace: "
            "use find_works twice with different title keywords (for example 'YOLO' vs "
            "'Faster R-CNN'), then call paper_profile for two distinct work_ids from the "
            "results. Note whether blurbs or metadata disagree on any factual point. "
            "Finish with final_answer and citations for both work_ids."
        ),
    ),
    (
        "v3_subagent_mesh_multi_tool",
        (
            "Does this workspace support real-time object detection trade-offs between speed "
            "and accuracy? Use at least two different tools among idea_search, paper_quote_search, "
            "workspace_inspect, and find_works; cite at least two distinct work_ids from tool "
            "outputs. If evidence is thin, say so explicitly. Finish with final_answer."
        ),
    ),
    (
        "b2_merge_provenance_probe",
        (
            "Pick one factual claim that could be checked against two different works in this "
            "workspace (use find_works + paper_profile). If tool outputs disagree, explain how "
            "you reconcile them and which work_id you trust more and why. "
            "Mention provenance (which tools) in the narrative. Finish with final_answer."
        ),
    ),
]


HEAVY_QUESTIONS: list[tuple[str, str]] = [
    (
        "multi_compare_bibliography",
        (
            "Compare two detector families in this workspace: (A) works whose titles mention "
            "'YOLO' and (B) works whose titles mention 'Faster R-CNN' or 'Mask R-CNN'. "
            "Use find_works with workspace_id for each query. Pick one best match per family, "
            "call paper_profile for each work_id, then format_bibliography_gost for exactly "
            "those two work_ids. Write a short contrastive paragraph (speed vs accuracy themes) "
            "grounded only in tool outputs. Finish with final_answer and citations for both works."
        ),
    ),
    (
        "graph_ego_methods",
        (
            "Pick one object-detection paper in this workspace (first call workspace_inspect "
            "mode=papers and take one concrete work_id). Then do ONE graph lookup only with "
            "edge_search for that work_id (do not run broad cypher). Summarize whether Method or "
            "Dataset neighbors are present from returned rows only; if none, state graph coverage "
            "gap explicitly. Keep it short and finish with final_answer."
        ),
    ),
    (
        "multi_evidence_speed_accuracy",
        (
            "What trade-offs between speed and accuracy for real-time object detection does this "
            "workspace support with evidence? Use at least two distinct retrieval paths among "
            "idea_search, paper_quote_search, and workspace_inspect (blurb or papers). "
            "Cite at least two different work_ids from tool outputs. If evidence is thin, "
            "state coverage gaps explicitly. Finish with final_answer."
        ),
    ),
]


DEFAULT_QUESTIONS: list[tuple[str, str]] = [
    (
        "catalog_resolution",
        (
            "In this workspace, find works whose titles mention 'Faster R-CNN' or 'Mask R-CNN' "
            "(use find_works with the workspace_id if titles are unknown). Pick one clear match "
            "and report year and venue using paper_profile. End with final_answer and citations."
        ),
    ),
    (
        "workspace_stats",
        (
            "How many works are in this workspace? Use workspace_inspect with mode=stats (and "
            "other tools only if needed). Summarize any claim-related or citation-related counts "
            "the tools return—do not invent numbers. Finish with final_answer."
        ),
    ),
    (
        "grounded_quote",
        (
            "Search this workspace for evidence about 'anchor-free' or 'anchor free' object "
            "detection (paper_quote_search and/or idea_search). Quote one short snippet with "
            "work_id in citations. Use final_answer when done."
        ),
    ),
]


def question_suite(suite: str) -> list[tuple[str, str]]:
    s = (suite or "default").strip().lower()
    if s == "heavy":
        return HEAVY_QUESTIONS
    if s == "full":
        return list(DEFAULT_QUESTIONS) + list(HEAVY_QUESTIONS)
    if s == "acceptance":
        return list(DEFAULT_QUESTIONS) + list(HEAVY_QUESTIONS) + list(ACCEPTANCE_V3_QUESTIONS)
    return DEFAULT_QUESTIONS
