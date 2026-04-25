"""LangGraph AgentState definition."""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    workspace_id: str | None
    citations: list[dict]
    tool_trace: list[dict]
    budget_remaining: int
    metadata: dict
