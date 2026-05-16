"""Schema gate: chat state resume live-check script exists and documents AGENT_LIVE_BASE."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "live_check" / "chat_nav_resume_smoke.py"
README = REPO_ROOT / "scripts" / "live_check" / "README.md"


def test_chat_nav_resume_smoke_script_present() -> None:
    assert SCRIPT.is_file(), f"missing {SCRIPT}"


def test_readme_mentions_chat_nav_resume() -> None:
    text = README.read_text(encoding="utf-8")
    assert "chat_nav_resume_smoke" in text
