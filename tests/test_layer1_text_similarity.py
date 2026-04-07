"""Unit tests for layer-1 text similarity helpers."""

from __future__ import annotations

import pytest

from eval.layer1.text_similarity import (
    author_names_difflib_macro,
    multiset_token_f1,
    rouge_l_f1,
)


def test_multiset_token_f1_identical() -> None:
    assert multiset_token_f1("Hello world", "hello  world") == pytest.approx(1.0)


def test_multiset_token_f1_partial() -> None:
    f1 = multiset_token_f1("a b c", "a b")
    assert 0.0 < f1 < 1.0


def test_rouge_l_f1_identical() -> None:
    assert rouge_l_f1("the cat sat", "the cat sat") == pytest.approx(1.0)


def test_rouge_l_f1_empty() -> None:
    assert rouge_l_f1("", "") == pytest.approx(1.0)
    assert rouge_l_f1("a", "") == pytest.approx(0.0)


def test_author_names_difflib_macro() -> None:
    m = author_names_difflib_macro(
        ["Joseph Redmon", "Jane Doe"],
        ["joseph redmon", "jane d."],
    )
    assert m > 0.85
