"""``final_answer`` tool args must reject empty user-visible text."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from science_graphrag.agent.tools.final_answer import FinalAnswerArgs


def test_final_answer_args_rejects_blank_answer() -> None:
    with pytest.raises(ValidationError):
        FinalAnswerArgs(answer="   ", citations=[])


def test_final_answer_args_accepts_stripped_nonempty() -> None:
    a = FinalAnswerArgs(answer="  hi  ", citations=[])
    assert a.answer == "hi"
