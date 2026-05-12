"""Tests for pre-compact message sanitizers (§10.5.4 / Wave H §H1)."""

from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage

from science_graphrag.agent.context.message_sanitizers import (
    redact_sensitive_material,
    sanitize_digest_dict_for_compact,
    sanitize_messages_for_summary,
)


def test_strip_images_from_multimodal_human() -> None:
    msgs = [
        HumanMessage(
            content=[
                {"type": "text", "text": "hello"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
            ]
        )
    ]
    out = sanitize_messages_for_summary(msgs)
    assert isinstance(out[0].content, list)
    assert all(
        not (isinstance(p, dict) and str(p.get("type") or "").lower() == "image_url")
        for p in out[0].content
    )


def test_strip_reinjected_blocks_from_human_string() -> None:
    raw = "<paper_sources_restored>\n- w1: x\n</paper_sources_restored>\n" "Question after?"
    msgs = [HumanMessage(content=raw)]
    out = sanitize_messages_for_summary(msgs)
    assert "<paper_sources_restored>" not in str(out[0].content)
    assert "Question after?" in str(out[0].content)


def test_sanitize_digest_dict_strips_markers() -> None:
    d = sanitize_digest_dict_for_compact(
        {
            "user_intent": "x",
            "answer_excerpt": "<client_history_digest>{}</client_history_digest> tail",
        }
    )
    assert "<client_history_digest>" not in d["answer_excerpt"]
    assert "tail" in d["answer_excerpt"]


# Wave H §H1: pre-compact sanitizers must redact secrets/PII before L4 LLM compact.
# Each fixture exercises one shape of leaked sensitive material that has been
# observed (or plausible) inside tool payloads or user fragments.

_AWS_ACCESS_KEY_TEST = "AKIA" + "EXAMPLEKEYAAAAAA"
_AWS_SECRET_KEY_TEST = "abcdEFGH/ijKL+mnOPqrSTUvwxYZ0123456789" + "AB"

_SECRET_FIXTURES: tuple[tuple[str, str, str, tuple[str, ...], str], ...] = (
    (
        "openai_key_in_user_intent",
        "set OPENAI_API_KEY=sk-1234567890ABCDEFghijKLMNopqr; please run extraction",
        "answer_excerpt",
        ("[REDACTED:openai_api_key]",),
        "please run extraction",
    ),
    (
        "anthropic_key_in_excerpt",
        "Tried Claude with sk-ant-api03-AAAA-BBBB-CCCC-DDDDDDDDDDDDDDDDDDDDDD then fell back",
        "answer_excerpt",
        ("[REDACTED:anthropic_api_key]",),
        "Tried Claude",
    ),
    (
        "openrouter_key_in_excerpt",
        "Bench runner used sk-or-v1-abcdefghijklmnopqrstuvwx for 3 hops",
        "answer_excerpt",
        ("[REDACTED:openrouter_api_key]",),
        "Bench runner used",
    ),
    (
        "bearer_in_user_intent",
        "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.aaaaaaaaaaaaaaaa.bbbbbbbb so we got 401",
        "user_intent",
        ("[REDACTED:bearer_token]",),
        "so we got 401",
    ),
    (
        "aws_keys_pair",
        f"credentials: {_AWS_ACCESS_KEY_TEST} aws_secret_access_key={_AWS_SECRET_KEY_TEST}",
        "answer_excerpt",
        ("[REDACTED:aws_access_key]", "[REDACTED:aws_secret]"),
        "credentials:",
    ),
    (
        "github_token_in_intent",
        "git push failed because ghp_AAAABBBBCCCCDDDDEEEEFFFFGGGGHHHH expired",
        "user_intent",
        ("[REDACTED:github_token]",),
        "git push failed",
    ),
    (
        "email_pii_preserved_context",
        "Contact alice.smith@example.org for the BERT corpus paper",
        "answer_excerpt",
        ("[REDACTED:email]",),
        "BERT corpus paper",
    ),
    (
        "generic_api_key_kv",
        'config{api_key:"abcdef0123456789MNOPQR"} loaded for run',
        "answer_excerpt",
        ("[REDACTED:api_key]",),
        "loaded for run",
    ),
)


@pytest.mark.parametrize(
    "fixture_id,raw,field,must_contain,must_preserve",
    _SECRET_FIXTURES,
    ids=[fx[0] for fx in _SECRET_FIXTURES],
)
def test_sanitize_digest_redacts_secret_fixture(
    fixture_id: str,
    raw: str,
    field: str,
    must_contain: tuple[str, ...],
    must_preserve: str,
) -> None:
    """Each known secret shape is redacted while surrounding context is preserved."""
    digest = {
        "user_intent": "ask",
        "answer_excerpt": "ans",
        "answer_class": "x",
        "tools_used": [],
    }
    digest[field] = raw
    cleaned = sanitize_digest_dict_for_compact(digest)
    out = cleaned[field]
    for stamp in must_contain:
        assert stamp in out, (fixture_id, stamp, out)
    assert must_preserve in out, (fixture_id, must_preserve, out)
    # No raw fragment of the secret should survive — heuristic: token contiguity.
    forbidden_substrings = (
        "sk-1234567890ABCDEFghij",
        "sk-ant-api03-AAAA-BBBB-CCCC",
        "sk-or-v1-abcdefghijklmnopqr",
        "eyJhbGciOiJIUzI1NiJ9.aaaaaaaaaaaaaaaa.bbbbbbbb",
        _AWS_ACCESS_KEY_TEST,
        _AWS_SECRET_KEY_TEST,
        "ghp_AAAABBBBCCCCDDDDEEEEFFFFGGGGHHHH",
        "alice.smith@example.org",
        '"abcdef0123456789MNOPQR"',
    )
    for needle in forbidden_substrings:
        assert needle not in out, (fixture_id, needle, out)


def test_sanitize_digest_preserves_useful_grounding() -> None:
    """Sanitizer must NOT mangle paper IDs, doc names, or numeric facts."""
    digest = {
        "user_intent": "Compare ROUGE-1 between BERT (work_id w-bert) and RoBERTa.",
        "answer_excerpt": (
            "BERT (Devlin et al., 2018, work_id=w-bert) reported ROUGE-1=0.47 on "
            "DailyMail. RoBERTa (work_id=w-roberta) tuned hyperparams. DOI: 10.18653/v1/N19-1423"
        ),
        "answer_class": "grounded_explanation",
        "tools_used": ["paper_quote_search", "paper_profile"],
    }
    cleaned = sanitize_digest_dict_for_compact(digest)
    excerpt = cleaned["answer_excerpt"]
    intent = cleaned["user_intent"]
    for token in ("w-bert", "w-roberta", "ROUGE-1=0.47", "10.18653/v1/N19-1423", "DailyMail"):
        assert token in excerpt
    assert "BERT" in intent and "RoBERTa" in excerpt
    assert "[REDACTED:" not in excerpt
    assert "[REDACTED:" not in intent


def test_redact_sensitive_material_idempotent() -> None:
    """Re-applying the redactor on already-redacted text is stable.

    Cache-prefix stability of L4 compact requires this — same input on retry
    must produce the same redacted blob.
    """
    raw = "OPENAI_API_KEY=sk-EXAMPLEEXAMPLEEXAMPLEEXAMPLE then email: bob@x.io"
    once = redact_sensitive_material(raw)
    twice = redact_sensitive_material(once)
    assert once == twice
    assert "[REDACTED:openai_api_key]" in twice
    assert "[REDACTED:email]" in twice


def test_redact_sensitive_material_handles_empty_and_none() -> None:
    """Sanitizer must be defensive against ``None`` and empty inputs."""
    assert redact_sensitive_material("") == ""
    assert redact_sensitive_material(None) == ""  # type: ignore[arg-type]


def test_sanitize_digest_dict_combined_markers_and_secrets() -> None:
    """Reinjected markers AND secrets in the same field are both handled."""
    digest = {
        "user_intent": "x",
        "answer_excerpt": (
            "<client_history_digest>{}</client_history_digest> "
            "saw key sk-ABCDEFGHIJKLMNOPQR and email a@b.io while reading w-bert"
        ),
        "answer_class": "x",
        "tools_used": [],
    }
    cleaned = sanitize_digest_dict_for_compact(digest)
    out = cleaned["answer_excerpt"]
    assert "<client_history_digest>" not in out
    assert "[REDACTED:openai_api_key]" in out
    assert "[REDACTED:email]" in out
    assert "w-bert" in out
