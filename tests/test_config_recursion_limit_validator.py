"""Validator: ``agent_supervisor_recursion_limit`` vs ``agent_max_tool_calls``.

Each ReAct cycle in the LangGraph agent uses ~4 hops (chat, route_*, tools, after_tools),
so the ``recursion_limit`` must comfortably fit ``agent_max_tool_calls`` cycles plus a small
envelope. We enforce ``recursion_limit >= 4 * max_tool_calls + 8`` at construction time so a
misconfiguration fails fast instead of producing ``GraphRecursionError`` mid-turn.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from science_graphrag.config import Settings


def test_default_settings_satisfy_recursion_validator() -> None:
    """Defaults (``max_tool_calls=12``, ``recursion_limit=64``) clear ``4*12 + 8 = 56``."""
    s = Settings()
    assert s.agent_supervisor_recursion_limit >= 4 * s.agent_max_tool_calls + 8


def test_recursion_limit_too_low_raises() -> None:
    """``max_tool_calls=20`` with ``recursion_limit=32`` violates ``4*20 + 8 = 88``."""
    with pytest.raises(ValidationError) as info:
        Settings(
            agent_max_tool_calls=20,
            agent_supervisor_recursion_limit=32,
        )
    err_text = str(info.value)
    assert "agent_supervisor_recursion_limit too low" in err_text
    assert "need >=" in err_text


def test_recursion_limit_at_lower_bound_is_accepted() -> None:
    """The lower bound itself (``4*N + 8``) is accepted."""
    s = Settings(
        agent_max_tool_calls=8,
        agent_supervisor_recursion_limit=4 * 8 + 8,
    )
    assert s.agent_supervisor_recursion_limit == 40
