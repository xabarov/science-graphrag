"""Product tools: research plan, structured user questions, brief summary."""

from __future__ import annotations

import time
import uuid
from typing import Any

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field, field_validator

from science_graphrag.agent.context.research_plan_session import merge_research_plan_items
from science_graphrag.agent.context.session_backend import get_session_memory_backend
from science_graphrag.agent.runtime_context import get_agent_graph_thread_id
from science_graphrag.config import Settings


def _research_plan_hint(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "research_plan_updated",
        "item_count": len(plan.get("items") or []),
        "updated_at": plan.get("updated_at"),
    }


def _user_question_hint(
    request_id: str, n_questions: int, questions: list[dict[str, Any]]
) -> dict[str, Any]:
    """Include bounded ``questions`` so the Ask UI can render without an extra round-trip."""
    return {
        "type": "user_question_asked",
        "request_id": request_id,
        "question_count": int(n_questions),
        "questions": list(questions[:8]),
    }


class ResearchPlanItem(BaseModel):
    id: str = Field(..., min_length=1, max_length=128)
    content: str = Field(..., min_length=1, max_length=2000)
    status: str = Field(default="pending")

    @field_validator("status", mode="before")
    @classmethod
    def _st(cls, v: object) -> str:
        s = str(v or "pending").strip().lower() or "pending"
        if s not in {"pending", "in_progress", "completed", "cancelled"}:
            return "pending"
        return s


class ResearchPlanWriteArgs(BaseModel):
    items: list[ResearchPlanItem] = Field(
        ...,
        description="TODO rows to merge into the thread research plan (upsert by id).",
    )


class QuestionOption(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    label: str = Field(..., min_length=1, max_length=512)


class StructuredQuestion(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    prompt: str = Field(..., min_length=1, max_length=2000)
    options: list[QuestionOption] = Field(..., min_length=2, max_length=16)
    allow_multiple: bool = Field(default=False)

    @field_validator("options")
    @classmethod
    def _unique_option_ids(cls, value: list[QuestionOption]) -> list[QuestionOption]:
        seen: set[str] = set()
        for option in value:
            if option.id in seen:
                raise ValueError(f"duplicate option id: {option.id}")
            seen.add(option.id)
        return value


class AskUserQuestionArgs(BaseModel):
    questions: list[StructuredQuestion] = Field(..., min_length=1, max_length=8)

    @field_validator("questions")
    @classmethod
    def _unique_question_ids(cls, value: list[StructuredQuestion]) -> list[StructuredQuestion]:
        seen: set[str] = set()
        for question in value:
            if question.id in seen:
                raise ValueError(f"duplicate question id: {question.id}")
            seen.add(question.id)
        return value


class BriefArgs(BaseModel):
    """Arguments for the ``brief`` tool (effective text capped at 240 chars in output)."""

    text: str = Field(
        ..., min_length=1, max_length=500, description="Short summary <=240 chars effective."
    )


def build_product_interaction_tools(settings: Settings) -> list[BaseTool]:
    """Return gated research-plan, ask-user, and brief tools for the agent registry."""
    tools: list[BaseTool] = []

    if settings.agent_research_plan_tool_enabled:

        @tool("research_plan_write", args_schema=ResearchPlanWriteArgs)
        def research_plan_write(items: list[ResearchPlanItem]) -> dict[str, Any]:
            """Merge structured TODO rows into ``session_meta.research_plan``."""
            tid = get_agent_graph_thread_id()
            if not tid:
                return {
                    "ok": False,
                    "error": "missing_thread_id",
                    "sse_hint": {"type": "research_plan_updated", "error": "missing_thread_id"},
                }
            raw_items = [it.model_dump() for it in items]
            plan = merge_research_plan_items(tid, raw_items, ui_mode="checklist")
            return {
                "ok": True,
                "item_count": len(plan.get("items") or []),
                "updated_at": plan.get("updated_at"),
                "sse_hint": _research_plan_hint(plan),
            }

        tools.append(research_plan_write)

    if settings.agent_ask_user_question_tool_enabled:

        @tool("ask_user_question", args_schema=AskUserQuestionArgs)
        def ask_user_question(questions: list[StructuredQuestion]) -> dict[str, Any]:
            """Ask a structured multi-choice question; persists pending envelope for next turn."""
            tid = get_agent_graph_thread_id()
            if not tid:
                return {
                    "ok": False,
                    "error": "missing_thread_id",
                    "sse_hint": {"type": "user_question_asked", "error": "missing_thread_id"},
                }
            request_id = str(uuid.uuid4())
            q_payload = []
            for q in questions:
                q_payload.append(
                    {
                        "id": q.id,
                        "prompt": q.prompt,
                        "options": [{"id": o.id, "label": o.label} for o in q.options],
                        "allow_multiple": bool(q.allow_multiple),
                    }
                )
            pending = {
                "request_id": request_id,
                "questions": q_payload,
                "created_at": time.time(),
            }
            get_session_memory_backend().patch_session_meta(
                tid, patch={"pending_user_question": pending}
            )
            return {
                "ok": True,
                "request_id": request_id,
                "questions": q_payload,
                "sse_hint": _user_question_hint(request_id, len(q_payload), q_payload),
            }

        tools.append(ask_user_question)

    if settings.agent_brief_output_enabled:

        @tool("brief", args_schema=BriefArgs)
        def brief(text: str) -> dict[str, Any]:
            """Synthetic short summary for history/share (<=240 chars)."""
            t = " ".join(str(text or "").split()).strip()
            if len(t) > 240:
                t = t[:237] + "..."
            return {
                "ok": True,
                "brief": t,
                "sse_hint": {"type": "brief_recorded", "chars": len(t)},
            }

        tools.append(brief)

    return tools
