"""Rule-based coordinator gate v0 (narrow deterministic guardrails + full rules path)."""

from __future__ import annotations

import re
from typing import Any, Literal

from science_graphrag.agent.chat_envelope import ANSWER_CLASSES

ConversationIntent = Literal["research_task", "small_talk", "meta", "ambiguous"]
ToolPolicy = Literal["no_tools", "clarify", "allow_tools"]
RouteHint = Literal["writer_agent", "retrieval_agent", "graph_agent", "finish"]

_GRAPH_INTENT_HINTS: tuple[str, ...] = (
    "lineage",
    "chain of papers",
    "who cited",
    "cites whom",
    "citation chain",
    "predecessor",
    "successor",
    "related version",
    "contradict",
    "neo4j",
    "cypher",
    "graph traversal",
    "compare these papers",
    "which paper influenced",
)

_HINT_RESEARCH_ANSWER_CLASSES = ANSWER_CLASSES - {"chat", "clarification"}

_SMALLTALK_LINE = re.compile(
    r"^(\s*)(привет|здравствуй(те)?|добрый\s+(день|вечер|утро)|"
    r"hi\b|hello\b|hey\b|good\s+(morning|afternoon|evening)\b|"
    r"howdy\b|gm\b|"
    r"ок(ей)?\b|okay\b|ok\b|"
    r"спасибо|благодарю|thanks|thank\s+you\b|thx\b|спс\b|"
    r"пока|bye\b|до\s+свидания)(\s*[!?.…]*)*$",
    re.IGNORECASE,
)

_META_LINE = re.compile(
    r"^(\s*)(что\s+ты\s+умеешь|кто\s+ты|чем\s+можешь\s+помочь|"
    r"what\s+can\s+you\s+do|who\s+are\s+you|help\b|помощь\b)(\s*[!.?…]*)?$",
    re.IGNORECASE,
)

_INVENTORY_STRONG = re.compile(
    r"(какие\s+стать|список\s+(стат|работ)|работ\s+в\s+(област|workspace)|"
    r"papers?\s+in\s+(the\s+)?workspace|works?\s+in\s+workspace|"
    r"how\s+many\s+papers?|сколько\s+стат)",
    re.IGNORECASE,
)

_RESEARCHISH = re.compile(
    r"(иде|idea|similar|semantic|chunk|цитат|quote|passage|snippet|"
    r"гост|gost|bibliograph|литератур|связ|path|cites|cypher|"
    r"автор|author|venue|dataset|метод|hypothesis|гипотез)",
    re.IGNORECASE,
)

_AMBIGUOUS_SCOPE = re.compile(
    r"(что\s+(тут|здесь|есть)|what('s|\s+is)\s+here|what\s+do\s+you\s+have)",
    re.IGNORECASE,
)

_RESEARCH_QUERY_START = re.compile(
    r"^(what|how|why|when|where|which|who|explain|describe|compare|summarize|list|find|show)\b|"
    r"^(что|как|почему|зачем|когда|где|какой|какая|объясни|опиши|сравни|перечисли|найди|покажи)\b",
    re.IGNORECASE,
)

FUZZY_RULES_V0_REASONS = frozenset(
    {
        "default_research_assumption",
        "vague_scope_question",
        "short_message_with_workspace",
    }
)


def _norm(q: str) -> str:
    return " ".join(str(q or "").strip().lower().split())


def _graph_intent_heuristic(text: str) -> bool:
    t = text.lower()
    return any(h in t for h in _GRAPH_INTENT_HINTS)


def explicit_research_signal(q_norm: str, answer_class_hint: str | None) -> bool:
    if answer_class_hint and answer_class_hint in _HINT_RESEARCH_ANSWER_CLASSES:
        return True
    if _INVENTORY_STRONG.search(q_norm):
        return True
    if _graph_intent_heuristic(q_norm):
        return True
    if _RESEARCHISH.search(q_norm):
        return True
    if any(
        x in q_norm
        for x in (
            "how many",
            "сколько",
            "список стат",
            "стать в области",
            "papers in",
            "works in workspace",
        )
    ):
        return True
    return False


def narrow_deterministic_classify(
    *,
    question: str,
    workspace_id: str | None,
    answer_class_hint: str | None,
) -> tuple[ConversationIntent, ToolPolicy, RouteHint, str, str] | None:
    """Return a policy tuple only for empty / small-talk / meta / explicit research; else None."""
    raw = str(question or "").strip()
    q_norm = _norm(raw)
    if not q_norm:
        return (
            "ambiguous",
            "clarify",
            "writer_agent",
            "empty_question",
            "clarification",
        )
    if _SMALLTALK_LINE.match(raw):
        return ("small_talk", "no_tools", "writer_agent", "small_talk_pattern", "chat")
    if _META_LINE.match(raw):
        return ("meta", "no_tools", "writer_agent", "meta_about_assistant", "chat")
    if explicit_research_signal(q_norm, answer_class_hint):
        sac = (
            str(answer_class_hint)
            if answer_class_hint and answer_class_hint in ANSWER_CLASSES
            else "grounded_explanation"
        )
        return ("research_task", "allow_tools", "retrieval_agent", "explicit_research_signal", sac)
    return None


def rules_v0_classify(
    *,
    question: str,
    workspace_id: str | None,
    session_summary: str = "",
    history_digest: list[dict[str, Any]] | None = None,
    answer_class_hint: str | None = None,
) -> tuple[ConversationIntent, ToolPolicy, RouteHint, str, str]:
    """Full rules_v0 path (backward compatible with pre-hybrid coordinator gate)."""
    _ = session_summary
    _ = history_digest
    raw = str(question or "").strip()
    q_norm = _norm(raw)
    has_ws = bool(str(workspace_id or "").strip())

    narrow = narrow_deterministic_classify(
        question=question,
        workspace_id=workspace_id,
        answer_class_hint=answer_class_hint,
    )
    if narrow is not None:
        return narrow

    if has_ws and _AMBIGUOUS_SCOPE.search(q_norm) and not _INVENTORY_STRONG.search(q_norm):
        return (
            "ambiguous",
            "clarify",
            "writer_agent",
            "vague_scope_question",
            "clarification",
        )

    word_count = len(q_norm.split())
    if (
        has_ws
        and word_count <= 2
        and len(q_norm) <= 20
        and "?" not in q_norm
        and not _RESEARCH_QUERY_START.search(q_norm.strip())
        and not explicit_research_signal(q_norm, answer_class_hint)
    ):
        return (
            "ambiguous",
            "clarify",
            "writer_agent",
            "short_message_with_workspace",
            "clarification",
        )

    sac = (
        str(answer_class_hint)
        if answer_class_hint and answer_class_hint in ANSWER_CLASSES
        else "grounded_explanation"
    )
    return ("research_task", "allow_tools", "retrieval_agent", "default_research_assumption", sac)
